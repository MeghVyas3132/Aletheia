import os
import logging
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents import FactChecker, ForensicExpert, TheJudge
from blockchain import submit_verdict_to_chain, lookup_cached_verdict, AptosVerdictClient, AptosVerdictClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MoveH-API")

app = FastAPI(title="MoveH API", description="AI Fact-Checking API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClaimRequest(BaseModel):
    claim: str

from fastapi.staticfiles import StaticFiles
from agents.shelby import Shelby

# Define absolute path for storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# Instantiate agents
fact_checker = FactChecker()
forensic_expert = ForensicExpert()
judge = TheJudge()
shelby = Shelby(storage_dir=STORAGE_DIR)

# Mount storage directory for downloads
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
app.mount("/download", StaticFiles(directory=STORAGE_DIR), name="download")

@app.get("/")
def read_root():
    return {"status": "online", "service": "MoveH API"}

@app.post("/verify_stream")
async def verify_claim_stream(request: ClaimRequest):
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")

    # Track processing time
    start_time = time.time()

    async def event_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing agents...'})}\n\n"
        
        a1_result = {}
        a2_result = {}
        queue = asyncio.Queue()
        
        async def run_fact_checker():
            try:
                async for event in fact_checker.astream_verify(claim):
                    for node, state in event.items():
                        if node == "strategist":
                             await queue.put({"type": "log", "agent": "FactChecker", "message": "Strategist generated search queries."})
                        elif node == "executor":
                             count = len(state.get('search_results', []))
                             await queue.put({"type": "log", "agent": "FactChecker", "message": f"Executor found {count} sources."})
                             await queue.put({"type": "sources", "data": state.get('search_results', [])})
                        elif node == "analyst":
                             await queue.put({"type": "log", "agent": "FactChecker", "message": "Analyst completed evaluation."})
                             if "evidence_dossier" in state:
                                  a1_result.update(state["evidence_dossier"])
            except Exception as e:
                logger.error(f"FactChecker error: {e}")
                await queue.put({"type": "error", "message": str(e)})

        async def run_forensic_expert():
            try:
                async for event in forensic_expert.astream_analyze(claim):
                    for node, state in event.items():
                        if node == "profiler":
                            await queue.put({"type": "log", "agent": "ForensicExpert", "message": "Profiler analyzed linguistic patterns."})
                        elif node == "detector":
                            await queue.put({"type": "log", "agent": "ForensicExpert", "message": "Detector checked for AI/manipulation."})
                        elif node == "auditor":
                            await queue.put({"type": "log", "agent": "ForensicExpert", "message": "Auditor calculated integrity score."})
                            if "forensic_log" in state:
                                a2_result.update(state["forensic_log"])
            except Exception as e:
                logger.error(f"ForensicExpert error: {e}")
                await queue.put({"type": "error", "message": str(e)})

        # Run agents in parallel
        task1 = asyncio.create_task(run_fact_checker())
        task2 = asyncio.create_task(run_forensic_expert())
        
        pending = {task1, task2}
        while pending:
            while not queue.empty():
                item = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
            
            done, pending = await asyncio.wait(pending, timeout=0.1, return_when=asyncio.FIRST_COMPLETED)
            
        # Drain remaining queue items
        while not queue.empty():
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"

        yield f"data: {json.dumps({'type': 'status', 'message': 'Adjudicating verdict...'})}\n\n"

        try:
            # Get base AEP from judge
            aep = await judge.aadjudicate(a1_result, a2_result)
            
            # ===================================================================
            # CRITICAL: Build COMPLETE AEP with all agent data for comprehensive PDF
            # ===================================================================
            processing_time = time.time() - start_time
            
            complete_aep = {
                "claim": claim,
                "claim_id": aep.get("claim_id", "N/A"),
                "evidence": {
                    "agent_1_fact_checker": a1_result,  # ← Full Agent 1 results
                    "agent_2_forensic_expert": a2_result # ← Full Agent 2 results
                },
                "verdict": aep.get("verdict", {}),
                "reasoning": aep.get("reasoning", ""),
                "chain_metadata": aep.get("chain_metadata", {}),
                "storage": aep.get("storage", {}),
                "processing_time": f"{processing_time:.1f}s",
                "timestamp": aep.get("timestamp", "")
            }
            
            # Generate comprehensive PDF Report via Shelby
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating comprehensive AEP Report...'})}\n\n"
            
            pdf_path = shelby.generate_report(complete_aep)
            
            # Upload to Shelby Protocol
            yield f"data: {json.dumps({'type': 'status', 'message': 'Uploading to Shelby...'})}\n\n"
            download_url = shelby.upload_report(pdf_path)
            
            # Update storage info with download URL
            complete_aep["storage"]["download_url"] = download_url
            complete_aep["storage"]["pdf_path"] = pdf_path
            
            # Submit to blockchain if configured (use async client since we're in async context)
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Checking blockchain for existing verdict...'})}\n\n"
                
                verdict_data = complete_aep.get("verdict", {})
                chain_meta = complete_aep.get("chain_metadata", {})
                claim_hash = chain_meta.get("claim_hash", "")
                
                # Debug: Log what we're submitting
                logger.info(f"[Blockchain] chain_metadata: {chain_meta}")
                logger.info(f"[Blockchain] verdict: {verdict_data.get('decision')}, confidence: {verdict_data.get('truth_probability')}")
                
                # Use async client directly to avoid "event loop already running" error
                async with AptosVerdictClient() as aptos_client:
                    # Check if verdict already exists on-chain and get the stored data
                    existing_verdict = await aptos_client.get_verdict(claim_hash)
                    
                    if existing_verdict:
                        # Verdict already exists - return the on-chain data
                        logger.info(f"✅ Verdict already exists on-chain for claim_hash: {claim_hash}")
                        logger.info(f"   On-chain verdict: {aptos_client.verdict_int_to_string(existing_verdict.verdict)}, confidence: {existing_verdict.confidence}")
                        logger.info(f"   Shelby CID: {existing_verdict.shelby_cid}")
                        
                        # Build direct download URL from stored Shelby CID
                        shelby_download_url = ""
                        if existing_verdict.shelby_cid:
                            shelby_download_url = f"https://api.shelbynet.shelby.xyz/shelby/v1/blobs/{existing_verdict.shelby_cid}"
                            logger.info(f"   Shelby Download URL: {shelby_download_url}")
                        
                        complete_aep["storage"]["aptos_status"] = "already_on_chain"
                        complete_aep["storage"]["claim_hash"] = claim_hash
                        complete_aep["storage"]["on_chain_verdict"] = {
                            "verdict": aptos_client.verdict_int_to_string(existing_verdict.verdict),
                            "confidence": existing_verdict.confidence,
                            "shelby_cid": existing_verdict.shelby_cid,
                            "shelby_download_url": shelby_download_url,
                            "timestamp": existing_verdict.timestamp
                        }
                        # Build explorer URL for the contract account (where verdicts are stored)
                        contract_explorer_url = f"https://explorer.aptoslabs.com/account/{aptos_client.MODULE_ADDRESS}/modules/run/verdict_registry/get_verdict?network=testnet"
                        complete_aep["storage"]["aptos_explorer_url"] = contract_explorer_url
                        
                        yield f"data: {json.dumps({'type': 'status', 'message': f'Verdict already on blockchain ✓ (confidence: {existing_verdict.confidence}%)'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Submitting new verdict to blockchain...'})}\n\n"
                        
                        # Extract Shelby CID from download URL
                        # URL format: https://api.shelbynet.shelby.xyz/shelby/v1/blobs/{address}/{blob_name}
                        shelby_cid = ""
                        if 'api.shelbynet.shelby.xyz' in download_url and '/blobs/' in download_url:
                            # Extract everything after /blobs/ (address + blob_name)
                            shelby_cid = download_url.split('/blobs/')[-1]
                        elif 'explorer.shelby.xyz' in download_url:
                            # Fallback: extract from explorer URL
                            shelby_cid = download_url.split('/account/')[-1] if '/account/' in download_url else ""
                        
                        logger.info(f"[Blockchain] Shelby CID: {shelby_cid}")
                        
                        aptos_tx_hash = await aptos_client.submit_verdict(
                            chain_metadata=chain_meta,
                            shelby_cid=shelby_cid,
                            verdict=verdict_data.get("decision", "UNKNOWN"),
                            confidence=int(verdict_data.get("truth_probability", 50))
                        )
                        
                        if aptos_tx_hash:
                            complete_aep["storage"]["aptos_tx"] = aptos_tx_hash
                            complete_aep["storage"]["claim_hash"] = claim_hash
                            complete_aep["storage"]["aptos_status"] = "submitted"
                            explorer_url = f"https://explorer.aptoslabs.com/txn/{aptos_tx_hash}?network=testnet"
                            complete_aep["storage"]["aptos_explorer_url"] = explorer_url
                            logger.info(f"✅ Blockchain submission successful: {aptos_tx_hash}")
                            logger.info(f"🔗 View on explorer: {explorer_url}")
                        else:
                            logger.warning("⚠️ Blockchain submission returned no tx hash")
                    
            except Exception as blockchain_error:
                logger.warning(f"Blockchain submission failed: {blockchain_error}")
                # Don't fail the whole request if blockchain fails
            
            # Build final response for frontend
            verdict_data = complete_aep.get("verdict", {})
            truth_prob = verdict_data.get("truth_probability", 50)
            storage_info = complete_aep.get("storage", {})
            
            final_response = {
                "claim": claim,
                "verdict": verdict_data.get("decision", "UNKNOWN"),
                "confidence_score": verdict_data.get("confidence_score", 0),
                "truth_probability": truth_prob,
                "verdict_text": verdict_data.get("verdict_text", ""),
                "confidence_level": verdict_data.get("confidence_level", "UNKNOWN"),
                "summary": complete_aep.get("reasoning", ""),
                "sources": a1_result.get("search_results", []),
                "forensic_analysis": {
                    "integrity_score": a2_result.get("integrity_score", 0),
                    "verdict": a2_result.get("verdict", "UNKNOWN"),
                    "ai_probability": a2_result.get("detection_summary", {}).get("ai_probability", 0),
                    "ai_indicators": a2_result.get("detection_summary", {}).get("indicators_found", []),
                    "penalties": a2_result.get("penalties_applied", []),
                    "checks_performed": a2_result.get("checks_performed", [])
                },
                "chain_metadata": complete_aep.get("chain_metadata", {}),
                "download_url": download_url,
                "processing_time": f"{processing_time:.1f}s",
                "aptos_tx": storage_info.get("aptos_tx"),
                "claim_hash": storage_info.get("claim_hash"),
                "aptos_status": storage_info.get("aptos_status", "submitted"),  # "submitted" or "already_on_chain"
                "aptos_explorer_url": storage_info.get("aptos_explorer_url"),
                "on_chain_verdict": storage_info.get("on_chain_verdict")  # Existing verdict data if already on-chain
            }
            
            yield f"data: {json.dumps({'type': 'result', 'data': final_response})}\n\n"
            
        except Exception as e:
            logger.error(f"Judge/Shelby error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    """
    Non-streaming endpoint for simple verification.
    Returns complete results including PDF download URL.
    """
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")
    
    start_time = time.time()
    
    try:
        # Check blockchain cache first
        cached_verdict = lookup_cached_verdict(claim)
        if cached_verdict and cached_verdict.is_fresh:
            logger.info(f"Cache hit for claim: {claim[:50]}...")
            return {
                "cached": True,
                "claim": claim,
                "verdict": cached_verdict.verdict,
                "confidence": cached_verdict.confidence,
                "shelby_cid": cached_verdict.shelby_cid,
                "claim_hash": cached_verdict.claim_hash
            }
        
        # Run agents in parallel
        logger.info("Running agents in parallel...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a1 = executor.submit(fact_checker.verify_claim, claim)
            future_a2 = executor.submit(forensic_expert.analyze_text, claim)
            
            a1_result = future_a1.result()
            a2_result = future_a2.result()
        
        # Get verdict from judge
        logger.info("Adjudicating verdict...")
        aep = judge.adjudicate(a1_result, a2_result)
        
        # Build complete AEP with all data
        processing_time = time.time() - start_time
        
        complete_aep = {
            "claim": claim,
            "claim_id": aep.get("claim_id", "N/A"),
            "evidence": {
                "agent_1_fact_checker": a1_result,
                "agent_2_forensic_expert": a2_result
            },
            "verdict": aep.get("verdict", {}),
            "reasoning": aep.get("reasoning", ""),
            "chain_metadata": aep.get("chain_metadata", {}),
            "storage": aep.get("storage", {}),
            "processing_time": f"{processing_time:.1f}s"
        }
        
        # Generate PDF
        logger.info("Generating PDF report...")
        pdf_path = shelby.generate_report(complete_aep)
        download_url = shelby.upload_report(pdf_path)
        
        complete_aep["storage"]["download_url"] = download_url
        complete_aep["storage"]["pdf_path"] = pdf_path
        
        # Submit to blockchain
        try:
            verdict_data = complete_aep.get("verdict", {})
            chain_meta = complete_aep.get("chain_metadata", {})
            
            # Extract Shelby CID from download URL
            # URL format: https://api.shelbynet.shelby.xyz/shelby/v1/blobs/{address}/{blob_name}
            shelby_cid = ""
            if 'api.shelbynet.shelby.xyz' in download_url and '/blobs/' in download_url:
                shelby_cid = download_url.split('/blobs/')[-1]
            elif 'explorer.shelby.xyz' in download_url:
                shelby_cid = download_url.split('/account/')[-1] if '/account/' in download_url else ""
            
            aptos_tx_hash = submit_verdict_to_chain(
                chain_metadata=chain_meta,
                shelby_cid=shelby_cid,
                verdict=verdict_data.get("decision", "UNKNOWN"),
                confidence=int(verdict_data.get("truth_probability", 50))
            )
            
            if aptos_tx_hash:
                complete_aep["storage"]["aptos_tx"] = aptos_tx_hash
                
        except Exception as blockchain_error:
            logger.warning(f"Blockchain submission failed: {blockchain_error}")
        
        # Return response
        verdict_data = complete_aep.get("verdict", {})
        storage_info = complete_aep.get("storage", {})
        
        return {
            "claim": claim,
            "verdict": verdict_data.get("decision", "UNKNOWN"),
            "confidence_score": verdict_data.get("confidence_score", 0),
            "truth_probability": verdict_data.get("truth_probability", 50),
            "summary": complete_aep.get("reasoning", ""),
            "sources": a1_result.get("search_results", []),
            "forensic_analysis": {
                "integrity_score": a2_result.get("integrity_score", 0),
                "ai_probability": a2_result.get("detection_summary", {}).get("ai_probability", 0),
                "penalties": a2_result.get("penalties_applied", [])
            },
            "chain_metadata": complete_aep.get("chain_metadata", {}),
            "download_url": download_url,
            "processing_time": f"{processing_time:.1f}s",
            "aptos_tx": complete_aep.get("storage", {}).get("aptos_tx", None),
            "claim_hash": storage_info.get("claim_hash"),
            "aptos_status": storage_info.get("aptos_status", "submitted"),
            "aptos_explorer_url": storage_info.get("aptos_explorer_url"),
            "on_chain_verdict": storage_info.get("on_chain_verdict")
        }
        
    except Exception as e:
        logger.error(f"Verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))