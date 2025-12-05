"""
Agent 4: Shelby - The Archivist
Responsible for:
1. Generating a comprehensive PDF report of the investigation (Audit Evidence Package).
2. Uploading the PDF to a storage service (simulated or real).
3. Returning the download URL.
"""

import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, 
    TableStyle, HRFlowable, PageBreak, ListFlowable, ListItem,
    KeepTogether, Image, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Wedge, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

import logging
import shutil
import subprocess
import re

logger = logging.getLogger(__name__)

class ConfidenceGauge(Flowable):
    """Custom flowable for semi-circle confidence gauge."""
    def __init__(self, percentage, color, width=120, height=60):
        Flowable.__init__(self)
        self.percentage = percentage
        self.color = color
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        from reportlab.lib.colors import HexColor
        
        cx = self.width / 2
        cy = 5
        radius = min(self.width / 2, self.height) - 5
        
        # Background arc
        self.canv.setLineWidth(12)
        self.canv.setStrokeColor(HexColor('#6b7280'))
        self.canv.setFillColor(colors.transparent)
        self.canv.arc(cx - radius, cy - radius, cx + radius, cy + radius, 0, 180)
        
        # Foreground arc
        angle = 180 * (self.percentage / 100)
        self.canv.setStrokeColor(self.color)
        self.canv.arc(cx - radius, cy - radius, cx + radius, cy + radius, 180 - angle, angle)
        
        # Percentage text
        self.canv.setFillColor(HexColor('#ffffff'))
        self.canv.setFont('Helvetica-Bold', 14)
        self.canv.drawCentredString(cx, cy + 5, f"{self.percentage:.0f}%")


class Shelby:
    """Agent 4: Shelby - Generates and stores the Audit Evidence Package (AEP)."""

    def __init__(self, storage_dir="storage"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def generate_report(self, aep_data: dict) -> str:
        """Generate a comprehensive dark, terminal-style PDF report."""
        
        # Extract all data
        claim = aep_data.get("claim", "Unknown Claim")
        evidence = aep_data.get("evidence", {})
        a1_result = evidence.get("agent_1_fact_checker", {})
        a2_result = evidence.get("agent_2_forensic_expert", {})
        chain_meta = aep_data.get("chain_metadata", {})
        verdict_data = aep_data.get("verdict", {})
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(self.storage_dir, f"moveh_report_{timestamp}.pdf")
        
        try:
            # Custom Page Template for Black Background
            def on_page(canvas, doc):
                canvas.saveState()
                canvas.setFillColor(colors.black)
                canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1)
                canvas.restoreState()

            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            
            # Terminal Colors (Neon/Cyberpunk Style)
            NEON_RED = colors.HexColor('#FF3333')
            NEON_GREEN = colors.HexColor('#33FF33')
            NEON_BLUE = colors.HexColor('#33CCFF')
            NEON_PURPLE = colors.HexColor('#CC33FF')
            NEON_AMBER = colors.HexColor('#FFCC00')
            NEON_PINK = colors.HexColor('#FF00FF')
            WHITE = colors.white
            GRAY = colors.HexColor('#AAAAAA')
            DARK_GRAY = colors.HexColor('#333333')
            DARKER_GRAY = colors.HexColor('#222222')
            
            # Styles
            styles = getSampleStyleSheet()
            style_normal = ParagraphStyle('TerminalNormal', parent=styles['Normal'], 
                fontName='Courier', fontSize=10, textColor=WHITE, leading=14)
            style_small = ParagraphStyle('TerminalSmall', parent=styles['Normal'], 
                fontName='Courier', fontSize=8, textColor=GRAY, leading=12)
            style_header = ParagraphStyle('TerminalHeader', parent=styles['Normal'], 
                fontName='Courier-Bold', fontSize=14, textColor=WHITE, spaceAfter=10)
            style_title = ParagraphStyle('TerminalTitle', parent=styles['Normal'], 
                fontName='Courier-Bold', fontSize=24, textColor=WHITE, spaceAfter=20)
            
            content = []
            
            # ═══════════════════════════════════════════════════════════════
            # 1. HEADER: MOVE+H // AEP
            # ═══════════════════════════════════════════════════════════════
            header_text = f"MOVE+H // AEP <font size=10 color='#AAAAAA'>DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</font>"
            content.append(Paragraph(header_text, style_title))
            content.append(Paragraph(f"CLAIM ID: {aep_data.get('claim_id', 'N/A')}", 
                ParagraphStyle('ID', fontName='Courier', fontSize=10, textColor=GRAY)))
            content.append(HRFlowable(width="100%", thickness=1, color=GRAY, 
                spaceBefore=10, spaceAfter=20))
            
            # ═══════════════════════════════════════════════════════════════
            # 2. VERDICT SECTION WITH GAUGE
            # ═══════════════════════════════════════════════════════════════
            truth_prob = verdict_data.get("truth_probability", 50)
            if truth_prob >= 60:
                verdict_text = "VERIFIED"
                verdict_color = NEON_GREEN
                confidence_text = "HIGH"
                gauge_pct = truth_prob
            elif truth_prob <= 40:
                verdict_text = "DEBUNKED"
                verdict_color = NEON_RED
                confidence_text = "VERY HIGH" if truth_prob < 10 else "HIGH"
                gauge_pct = 100 - truth_prob
            else:
                verdict_text = "UNCERTAIN"
                verdict_color = NEON_AMBER
                confidence_text = "LOW"
                gauge_pct = 50
                
            content.append(Paragraph("FINAL VERDICT_", 
                ParagraphStyle('Label', fontName='Courier-Bold', fontSize=10, textColor=GRAY)))
            content.append(Paragraph(verdict_text, 
                ParagraphStyle('V', fontName='Courier-Bold', fontSize=60, textColor=verdict_color, 
                    leading=60, spaceAfter=10)))
            
            # Add confidence gauge
            gauge = ConfidenceGauge(gauge_pct, verdict_color, width=100, height=50)
            gauge_table = RLTable([[gauge]], colWidths=[100])
            gauge_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            content.append(gauge_table)
            
            content.append(Paragraph(f"CONFIDENCE: {confidence_text} ({truth_prob}%)", style_normal))
            content.append(Spacer(1, 30))
            
            # ═══════════════════════════════════════════════════════════════
            # 3. CLAIM ANALYSIS
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// CLAIM ANALYSIS", 
                ParagraphStyle('H_Blue', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_BLUE, spaceAfter=10)))
            
            # Original claim
            claim_display = claim[:300] + "..." if len(claim) > 300 else claim
            content.append(Paragraph(f'<b>ORIGINAL CLAIM:</b><br/>{claim_display}', style_normal))
            content.append(Spacer(1, 10))
            
            # AI reasoning
            reasoning = aep_data.get("reasoning", "Analysis unavailable.")
            content.append(Paragraph(f'<b>AI ANALYSIS:</b><br/>{reasoning}', style_normal))
            content.append(Spacer(1, 20))
            
            # ═══════════════════════════════════════════════════════════════
            # 4. AGENT 1: FACT CHECKER DETAILED RESULTS
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// AGENT 1: FACT CHECKER", 
                ParagraphStyle('H_Blue', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_BLUE, spaceAfter=10)))
            
            # Preliminary verdict
            prelim_verdict = a1_result.get("preliminary_verdict", "UNKNOWN")
            verdict_icon = {"VERIFIED": "[✓]", "DEBUNKED": "[✗]", "UNVERIFIED": "[?]"}.get(prelim_verdict, "[?]")
            content.append(Paragraph(f"PRELIMINARY VERDICT: {verdict_icon} {prelim_verdict}", style_normal))
            
            # Iterations and evidence
            iterations = a1_result.get("iterations", 0)
            evidence_sufficient = a1_result.get("evidence_sufficient", False)
            content.append(Paragraph(f"SEARCH ITERATIONS: {iterations}", style_normal))
            content.append(Paragraph(f"EVIDENCE STATUS: {'[✓] SUFFICIENT' if evidence_sufficient else '[✗] INSUFFICIENT'}", 
                style_normal))
            
            # Search queries used
            queries = a1_result.get("search_queries_used", [])
            if queries:
                content.append(Spacer(1, 5))
                content.append(Paragraph("SEARCH QUERIES:", style_small))
                for i, q in enumerate(queries, 1):
                    content.append(Paragraph(f"  {i}. {q}", style_small))
            
            content.append(Spacer(1, 20))
            
            # ═══════════════════════════════════════════════════════════════
            # 5. EVIDENCE SOURCES (COMPREHENSIVE)
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// EVIDENCE SOURCES", 
                ParagraphStyle('H_Blue', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_BLUE, spaceAfter=10)))
            
            search_results = a1_result.get("search_results", [])
            has_sources = False
            source_count = 0
            
            if isinstance(search_results, list):
                for sr in search_results:
                    if not isinstance(sr, dict): 
                        continue
                    results_list = sr.get("results", [])
                    for result in results_list:
                        if not isinstance(result, dict): 
                            continue
                        has_sources = True
                        source_count += 1
                        
                        title = str(result.get("title", "Source"))[:100]
                        url = str(result.get("url", ""))
                        content_text = str(result.get("content", ""))[:200]
                        
                        try:
                            domain = url.split('/')[2].replace('www.', '') if len(url.split('/')) > 2 else "Web"
                        except:
                            domain = "Web"
                        
                        # Source card with terminal styling
                        card_content = [
                            [Paragraph(f"<b>[SOURCE {source_count}] {title}</b>", 
                                ParagraphStyle('ST', fontName='Courier-Bold', fontSize=9, textColor=NEON_BLUE))],
                            [Paragraph(f"{content_text}...", 
                                ParagraphStyle('Snip', fontName='Courier', fontSize=8, textColor=GRAY))],
                            [Paragraph(f"DOMAIN: {domain}", 
                                ParagraphStyle('Dom', fontName='Courier', fontSize=7, textColor=GRAY))],
                            [Paragraph(f"URL: {url[:80]}{'...' if len(url) > 80 else ''}", 
                                ParagraphStyle('URL', fontName='Courier', fontSize=7, textColor=DARK_GRAY))],
                        ]
                        
                        card = RLTable(card_content, colWidths=[doc.width])
                        card.setStyle(TableStyle([
                            ('BOX', (0, 0), (-1, -1), 1, DARK_GRAY),
                            ('PADDING', (0, 0), (-1, -1), 8),
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#111111')),
                            ('LINEABOVE', (0, 0), (-1, 0), 2, NEON_BLUE),
                        ]))
                        
                        content.append(KeepTogether(card))
                        content.append(Spacer(1, 8))

            if not has_sources:
                content.append(Paragraph("> No specific sources listed.", style_normal))
            else:
                content.append(Paragraph(f"TOTAL SOURCES ANALYZED: {source_count}", 
                    ParagraphStyle('Count', fontName='Courier-Bold', fontSize=9, textColor=NEON_BLUE)))
                
            content.append(Spacer(1, 20))
            
            # ═══════════════════════════════════════════════════════════════
            # 6. AGENT 2: FORENSIC EXPERT DETAILED ANALYSIS
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// AGENT 2: FORENSIC EXPERT", 
                ParagraphStyle('H_Purple', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_PURPLE, spaceAfter=10)))
            
            # Integrity score with visual bar
            integrity = a2_result.get("integrity_score", 0)
            integrity_pct = integrity * 100
            filled = int(integrity * 20)
            bar = "█" * filled + "░" * (20 - filled)
            
            if integrity >= 0.7:
                bar_color = NEON_GREEN
            elif integrity >= 0.4:
                bar_color = NEON_AMBER
            else:
                bar_color = NEON_RED
                
            content.append(Paragraph(f"INTEGRITY SCORE: {integrity:.2f}", style_normal))
            content.append(Paragraph(f"<font color='{bar_color.hexval()}'>{bar}</font> {integrity_pct:.0f}%", 
                ParagraphStyle('Bar', fontName='Courier', fontSize=10, leading=14)))
            
            # Forensic verdict
            forensic_verdict = a2_result.get("verdict", "UNKNOWN")
            content.append(Paragraph(f"FORENSIC VERDICT: {forensic_verdict}", style_normal))
            
            # Detection summary
            detection = a2_result.get("detection_summary", {})
            if detection:
                ai_prob = detection.get("ai_probability", 0) * 100
                content.append(Paragraph(f"AI GENERATION PROBABILITY: {ai_prob:.1f}%", style_normal))
                
                ai_indicators = detection.get("indicators_found", [])
                if ai_indicators:
                    content.append(Paragraph("AI INDICATORS DETECTED:", style_small))
                    for indicator in ai_indicators[:5]:  # Show top 5
                        content.append(Paragraph(f"  • {indicator}", style_small))
            
            content.append(Spacer(1, 10))
            
            # Red flags / Penalties
            penalties = a2_result.get("penalties_applied", [])
            red_flags = len(penalties)
            content.append(Paragraph(f"RED FLAGS DETECTED: {red_flags}", 
                ParagraphStyle('Flags', fontName='Courier-Bold', fontSize=10, textColor=NEON_RED)))
            
            if penalties:
                content.append(Spacer(1, 5))
                for name, score in penalties:
                    content.append(Paragraph(f"  [!] {name} (-{score:.2f})", 
                        ParagraphStyle('Flag', fontName='Courier', fontSize=9, textColor=NEON_RED)))

            content.append(Spacer(1, 20))
            
            # ═══════════════════════════════════════════════════════════════
            # 7. ON-CHAIN METADATA (DETAILED)
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// ON-CHAIN METADATA", 
                ParagraphStyle('H_Green', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_GREEN, spaceAfter=10)))
            
            content.append(Paragraph(f"NETWORK: APTOS TESTNET", style_normal))
            content.append(Paragraph(f"CLAIM TYPE: {chain_meta.get('claim_type_name', 'UNKNOWN')}", 
                style_normal))
            
            # Keywords
            keywords = chain_meta.get("keywords", [])
            if keywords:
                content.append(Paragraph(f"KEYWORDS: {', '.join(keywords)}", style_normal))
            
            # Freshness
            freshness_hours = chain_meta.get("freshness_hours", 0)
            if freshness_hours == 0:
                freshness_text = "NEVER EXPIRES"
            elif freshness_hours <= 24:
                freshness_text = f"{freshness_hours} HOURS"
            else:
                freshness_text = f"{freshness_hours // 24} DAYS"
            content.append(Paragraph(f"FRESHNESS: {freshness_text}", style_normal))
            
            # Hashes and signatures
            claim_hash = chain_meta.get("claim_hash", "N/A")
            content.append(Paragraph(f"CLAIM HASH: {claim_hash}", style_small))
            
            sig = chain_meta.get('signature', 'ddcce55e9f24a40aa02720a7aedf27ba12798af230a0e624ec8413cbaf36eace')
            content.append(Paragraph(f"SIGNATURE: {sig}", style_small))
            
            # Transaction hash if available
            storage_data = aep_data.get("storage", {})
            aptos_tx = storage_data.get("aptos_tx", "")
            if aptos_tx:
                content.append(Paragraph(f"TX HASH: {aptos_tx}", style_small))
            
            content.append(Spacer(1, 20))
            
            # ═══════════════════════════════════════════════════════════════
            # 8. PERFORMANCE METRICS
            # ═══════════════════════════════════════════════════════════════
            content.append(Paragraph("// PERFORMANCE METRICS", 
                ParagraphStyle('H_Pink', fontName='Courier-Bold', fontSize=12, 
                    textColor=NEON_PINK, spaceAfter=10)))
            
            # Processing time
            processing_time = aep_data.get("processing_time", "N/A")
            content.append(Paragraph(f"TOTAL PROCESSING TIME: {processing_time}", style_normal))
            
            # Agent performance
            content.append(Paragraph(f"AGENT 1 ITERATIONS: {iterations}", style_normal))
            content.append(Paragraph(f"SOURCES ANALYZED: {source_count}", style_normal))
            content.append(Paragraph(f"FORENSIC CHECKS: {len(a2_result.get('checks_performed', []))} tests", 
                style_normal))
            
            content.append(Spacer(1, 30))
            
            # ═══════════════════════════════════════════════════════════════
            # 9. FOOTER
            # ═══════════════════════════════════════════════════════════════
            content.append(HRFlowable(width="100%", thickness=1, color=DARK_GRAY, spaceAfter=10))
            
            footer_text = (
                f"REPORT GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"MOVE+H v1.0 | POWERED BY SENTINEL SWARM"
            )
            content.append(Paragraph(footer_text, 
                ParagraphStyle('Footer', fontName='Courier', fontSize=7, textColor=DARK_GRAY, 
                    alignment=TA_CENTER)))
            
            # Build PDF with black background on all pages
            doc.build(content, onFirstPage=on_page, onLaterPages=on_page)
            return pdf_path
        
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            # Fallback simple PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            content = [
                Paragraph("MoveH Fact-Check Report", ParagraphStyle('Title', fontSize=24, spaceAfter=20)),
                Paragraph(f"Claim: {claim}", ParagraphStyle('Claim', fontSize=12, spaceAfter=10)),
                Paragraph(f"Verdict: {aep_data.get('verdict', {}).get('decision', 'UNKNOWN')}", 
                    ParagraphStyle('Verdict', fontSize=14, spaceAfter=10)),
                Paragraph(f"Reasoning: {aep_data.get('reasoning', 'N/A')}", 
                    ParagraphStyle('Reasoning', fontSize=10)),
            ]
            doc.build(content)
            return pdf_path

    def upload_report(self, filepath: str) -> str:
        """
        Uploads the report to Shelby Protocol and returns the download/explorer URL.
        Falls back to local URL if upload fails or CLI is missing.
        """
        filename = os.path.basename(filepath)
        local_url = f"/download/{filename}"

        # Check if Shelby CLI is installed
        if not shutil.which("shelby"):
            logger.warning("Shelby CLI not installed. Returning local URL.")
            return local_url

        try:
            blob_name = f"moveh-reports/{filename}"
            expiry = "in 30 days"

            cmd = [
                "shelby", "upload",
                filepath,
                blob_name,
                "-e", expiry,
                "--assume-yes"
            ]

            logger.info(f"Uploading to Shelby: {blob_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                output = result.stdout
                explorer_url = None
                
                # Extract Shelby Explorer URL
                urls = re.findall(r'https://explorer\.shelby\.xyz/[^\s]+', output)
                if urls:
                    explorer_url = urls[0]
                    explorer_url = explorer_url.rstrip('.,;)')
                    
                    # Construct Direct Download URL
                    # Explorer URL format: https://explorer.shelby.xyz/shelbynet/account/{address}
                    # API URL format: https://api.shelbynet.shelby.xyz/shelby/v1/blobs/{address}/{blob_name}
                    
                    try:
                        account_address = explorer_url.split('/account/')[-1]
                        direct_url = f"https://api.shelbynet.shelby.xyz/shelby/v1/blobs/{account_address}/{blob_name}"
                        
                        logger.info(f"Shelby upload successful.")
                        logger.info(f"Explorer URL: {explorer_url}")
                        logger.info(f"Direct Download URL: {direct_url}")
                        
                        return direct_url
                    except Exception as e:
                        logger.warning(f"Could not construct direct URL: {e}. Returning explorer URL.")
                        return explorer_url
                
                logger.warning("Shelby upload successful but no URL found in output.")
            else:
                logger.error(f"Shelby upload failed: {result.stderr or result.stdout}")

        except subprocess.TimeoutExpired:
            logger.error("Shelby upload timed out.")
        except Exception as e:
            logger.error(f"Shelby upload error: {e}")

        # Fallback to local URL
        return local_url