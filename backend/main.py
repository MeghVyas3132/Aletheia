"""
🛡️ Sentinel Swarm - TruthChain Protocol CLI

A multi-agent fact-checking system using LangGraph and Gemini 2.5 Flash.
Verifies claims through:
- Agent 1: Fact Checker (Web Search & Evidence Analysis)
- Agent 2: Forensic Expert (Linguistic & AI Detection)
- Agent 3: The Judge (Consensus & Final Verdict)
"""

import os
import sys
import time
import logging
import subprocess
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import BytesIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
from rich.markdown import Markdown
from rich import box

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
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

# Import agents from organized folder
from agents import FactChecker, ForensicExpert, TheJudge, ClaimType

# Import blockchain client
from blockchain import submit_verdict_to_chain, check_verdict_exists, lookup_cached_verdict, CachedVerdict

# Initialize Rich console
console = Console()


# ============ Logging Configuration ============
def setup_logging() -> logging.Logger:
    """Configure logging with file handler."""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"sentinel_swarm_{timestamp}.log")
    
    logger = logging.getLogger("SentinelSwarm")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)
    
    logger.info("=" * 60)
    logger.info("Sentinel Swarm - TruthChain Protocol Started")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)
    
    return logger, log_file


logger, log_file = setup_logging()


# ============ Input Validation ============
def validate_claim(text: str) -> tuple[bool, str]:
    """
    Validate if the input is a claim statement, not a question.
    
    Args:
        text: The user input to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    text = text.strip()
    
    # Check if empty
    if not text:
        return False, "Please enter a claim to verify."
    
    # Question indicators
    question_starters = [
        "what", "who", "where", "when", "why", "how", 
        "is", "are", "was", "were", "will", "would", "could", "should",
        "do", "does", "did", "can", "has", "have", "had",
        "which", "whom", "whose"
    ]
    
    first_word = text.lower().split()[0] if text.split() else ""
    
    # Check if starts with question word or ends with ?
    is_question = (
        text.endswith("?") or 
        first_word in question_starters
    )
    
    if is_question:
        error_msg = """
[bold red]❌ Questions cannot be fact-checked![/bold red]

MoveH verifies [bold]claim statements[/bold], not questions.

[bold cyan]❌ Don't ask:[/bold cyan]
  • "Is Tesla buying Twitter?"
  • "Did Nvidia invest in Nokia?"
  • "What happened to Bitcoin?"

[bold green]✅ Instead, make a claim:[/bold green]
  • "Tesla is acquiring Twitter for $100 billion"
  • "Nvidia invested in Nokia"
  • "Bitcoin crashed to $10,000 today"
  • "Apple reported record Q4 earnings of $1.95 per share"
  • "Elon Musk announced SpaceX Mars mission for 2026"

[dim]Tip: State the information as if it were a fact, and we'll verify it![/dim]
"""
        return False, error_msg
    
    # Check minimum length (at least 3 words for a meaningful claim)
    word_count = len(text.split())
    if word_count < 3:
        return False, "[yellow]Claim too short. Please provide more details.[/yellow]"
    
    return True, ""


# ============ UI Helper Functions ============
def print_header():
    """Print the application header."""
    header = """
[bold cyan]╔═══════════════════════════════════════════════════════════════╗
║  🛡️  SENTINEL SWARM - TruthChain Protocol                      ║
║     Multi-Agent Fact-Checking System                           ║
╚═══════════════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(header)


def print_claim_box(claim: str):
    """Print the claim being analyzed."""
    console.print(Panel(
        f"[bold white]{claim}[/bold white]",
        title="[bold yellow]📋 Claim to Verify[/bold yellow]",
        border_style="yellow",
        padding=(1, 2)
    ))


def create_spinner_status(message: str):
    """Create a progress spinner for status updates."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        transient=True,
        console=console
    )


def run_with_spinner(message: str, func, *args, **kwargs):
    """Run a function with a spinner animation."""
    with create_spinner_status(message) as progress:
        task = progress.add_task(message, total=None)
        result = func(*args, **kwargs)
        progress.remove_task(task)
    return result


def print_agent_header(agent_num: int, agent_name: str, icon: str, color: str):
    """Print an agent section header."""
    console.print()
    console.print(Panel(
        f"[bold {color}]{icon} {agent_name}[/bold {color}]",
        border_style=color,
        box=box.DOUBLE
    ))


def print_fact_checker_results(dossier: dict):
    """Print Fact Checker (Agent 1) results."""
    verdict = dossier.get("preliminary_verdict", "UNVERIFIED")
    iterations = dossier.get("iterations", 1)
    evidence_sufficient = dossier.get("evidence_sufficient", False)
    queries = dossier.get("search_queries_used", [])
    
    verdict_colors = {"VERIFIED": "green", "DEBUNKED": "red", "UNVERIFIED": "yellow"}
    verdict_icons = {"VERIFIED": "✅", "DEBUNKED": "❌", "UNVERIFIED": "⚠️"}
    color = verdict_colors.get(verdict, "yellow")
    icon = verdict_icons.get(verdict, "❓")
    
    # Results table
    table = Table(show_header=False, box=box.ROUNDED, border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Verdict", f"[bold {color}]{icon} {verdict}[/bold {color}]")
    table.add_row("Iterations", str(iterations))
    table.add_row("Evidence", "[green]✓ Sufficient[/green]" if evidence_sufficient else "[yellow]⚠ Insufficient[/yellow]")
    table.add_row("Queries Used", str(len(queries)))
    
    console.print(table)
    
    # Show queries
    if queries:
        console.print("\n[dim]Search Queries:[/dim]")
        for i, q in enumerate(queries, 1):
            console.print(f"  [cyan]{i}.[/cyan] {q}")


def print_forensic_results(forensic_log: dict):
    """Print Forensic Expert (Agent 2) results."""
    score = forensic_log.get("integrity_score", 0)
    verdict = forensic_log.get("verdict", "UNKNOWN")
    penalties = forensic_log.get("penalties_applied", [])
    
    # Score color
    if score >= 0.7:
        score_color = "green"
    elif score >= 0.4:
        score_color = "yellow"
    else:
        score_color = "red"
    
    # Score bar
    filled = int(score * 20)
    bar = "█" * filled + "░" * (20 - filled)
    
    # Results table
    table = Table(show_header=False, box=box.ROUNDED, border_style="magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Integrity Score", f"[bold {score_color}]{score:.2f}[/bold {score_color}]")
    table.add_row("Score Bar", f"[{score_color}]{bar}[/{score_color}]")
    table.add_row("Verdict", f"[bold]{verdict}[/bold]")
    table.add_row("Red Flags", str(len(penalties)))
    
    console.print(table)
    
    # Show penalties if any
    if penalties:
        console.print("\n[dim]Penalties Applied:[/dim]")
        for name, penalty in penalties:
            console.print(f"  [red]- {penalty:.2f}[/red] → {name}")


def print_judge_results(aep: dict):
    """Print The Judge (Agent 3) final verdict with probability language."""
    verdict_data = aep.get("verdict", {})
    verdict = verdict_data.get("decision", "UNKNOWN")
    score = verdict_data.get("confidence_score", 0)
    truth_prob = verdict_data.get("truth_probability", 50)
    verdict_text = verdict_data.get("verdict_text", "")
    confidence = verdict_data.get("confidence_level", "UNKNOWN")
    reasoning = aep.get("reasoning", "No reasoning provided.")
    
    # Get chain metadata
    chain_meta = aep.get("chain_metadata", {})
    keywords = chain_meta.get("keywords", [])
    claim_type_name = chain_meta.get("claim_type_name", "UNKNOWN")
    freshness_hours = chain_meta.get("freshness_hours", 0)
    
    # Probability-based styling
    if truth_prob >= 60:
        color = "green"
        icon = "✅"
        prob_display = f"{truth_prob:.0f}% likely TRUE"
    elif truth_prob <= 40:
        color = "red"
        icon = "❌"
        prob_display = f"{100-truth_prob:.0f}% likely FALSE"
    else:
        color = "yellow"
        icon = "⚠️"
        prob_display = f"Uncertain ({truth_prob:.0f}%)"
    
    # Final verdict panel with probability
    console.print()
    console.print(Panel(
        f"[bold {color}]{icon}  {prob_display}[/bold {color}]\n\n"
        f"[dim]{verdict_text}[/dim]",
        title="[bold]⚖️ VERDICT[/bold]",
        border_style=color,
        padding=(1, 3)
    ))
    
    # Summary reasoning
    console.print("\n[bold cyan]Summary:[/bold cyan]")
    console.print(Panel(reasoning, border_style="dim", padding=(0, 2)))
    
    # Chain metadata info
    console.print("\n[bold magenta]🔗 Chain Metadata:[/bold magenta]")
    meta_table = Table(show_header=False, box=box.SIMPLE, border_style="dim")
    meta_table.add_column("Key", style="cyan")
    meta_table.add_column("Value", style="white")
    
    meta_table.add_row("Keywords", ", ".join(keywords) if keywords else "N/A")
    meta_table.add_row("Claim Type", f"[yellow]{claim_type_name}[/yellow]")
    
    # Format freshness
    if freshness_hours == 0:
        freshness_display = "[green]Never expires[/green]"
    elif freshness_hours <= 24:
        freshness_display = f"[red]{freshness_hours} hours[/red]"
    else:
        freshness_display = f"[yellow]{freshness_hours // 24} days[/yellow]"
    meta_table.add_row("Freshness", freshness_display)
    
    # Show full claim hash for on-chain verification
    full_hash = chain_meta.get('claim_hash', 'N/A')
    meta_table.add_row("Claim Hash", f"[cyan]{full_hash}[/cyan]")
    
    console.print(meta_table)
    
    # Confidence info
    console.print(f"\n[dim]Confidence: {score:.0%} ({confidence})[/dim]")
    console.print(f"[dim]🔗 Report ID: {aep.get('claim_id', 'N/A')}[/dim]")


def print_summary(aep: dict, elapsed_time: float):
    """Print final summary with probability language."""
    verdict_data = aep.get("verdict", {})
    truth_prob = verdict_data.get("truth_probability", 50)
    
    if truth_prob >= 60:
        color, icon = "green", "✅"
        verdict_display = f"{truth_prob:.0f}% likely TRUE"
    elif truth_prob <= 40:
        color, icon = "red", "❌"
        verdict_display = f"{100-truth_prob:.0f}% likely FALSE"
    else:
        color, icon = "yellow", "⚠️"
        verdict_display = f"Uncertain ({truth_prob:.0f}%)"
    
    console.print()
    console.print(Panel(
        f"[bold white]Analysis Complete[/bold white]\n\n"
        f"Verdict: [bold {color}]{icon} {verdict_display}[/bold {color}]\n"
        f"Processing Time: [cyan]{elapsed_time:.1f}s[/cyan]\n"
        f"Log File: [dim]{log_file}[/dim]",
        title="[bold green]✅ Summary[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))


# ============ PDF Report Generation ============

class ConfidenceGauge(Flowable):
    """Custom flowable for semi-circle confidence gauge."""
    def __init__(self, percentage, color, width=120, height=60):
        Flowable.__init__(self)
        self.percentage = percentage
        self.color = color
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        # This tells the Table exactly how much space to reserve
        return self.width, self.height

    def draw(self):
        from reportlab.lib.colors import HexColor
        
        # Center the drawing in the available space
        cx = self.width / 2
        cy = 5  # Bottom padding
        radius = min(self.width / 2, self.height) - 5
        
        # Background arc (darker gray for contrast with white progress)
        self.canv.setLineWidth(12)
        self.canv.setStrokeColor(HexColor('#6b7280'))
        self.canv.setFillColor(colors.transparent)
        # arc(x1, y1, x2, y2, startAng, extent)
        self.canv.arc(cx - radius, cy - radius, cx + radius, cy + radius, 0, 180)
        
        # Foreground arc (white progress on dark background)
        angle = 180 * (self.percentage / 100)
        self.canv.setStrokeColor(self.color)
        self.canv.arc(cx - radius, cy - radius, cx + radius, cy + radius, 180 - angle, angle)
        
        # Percentage Text
        self.canv.setFillColor(HexColor('#ffffff')) # White text looks better on colored headers
        self.canv.setFont('Helvetica-Bold', 14)
        self.canv.drawCentredString(cx, cy + 5, f"{self.percentage:.0f}%")

class DonutChart(Flowable):
    """Custom flowable for donut chart."""
    def __init__(self, percentage, color, size=50, label=""):
        Flowable.__init__(self)
        self.percentage = percentage
        self.color = color
        self.size = size
        self.label = label
        self.width = size
        self.height = size + 15 # Reserve space for label

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        from reportlab.lib.colors import HexColor
        
        cx = self.width / 2
        cy = self.height - (self.size / 2) # Top aligned
        radius = self.size / 2
        inner_radius = radius * 0.6
        
        # Background circle
        self.canv.setFillColor(HexColor('#e2e8f0'))
        self.canv.setStrokeColor(colors.transparent)
        self.canv.circle(cx, cy, radius, fill=1, stroke=0)
        
        # Wedge (Foreground)
        if self.percentage > 0:
            self.canv.setFillColor(self.color)
            angle = 360 * (self.percentage / 100)
            p = self.canv.beginPath()
            p.moveTo(cx, cy)
            # arcTo draws a curve. simplified wedge approach:
            p.arc(cx - radius, cy - radius, cx + radius, cy + radius, 90, angle) 
            p.lineTo(cx, cy)
            p.close()
            self.canv.drawPath(p, fill=1, stroke=0)
        
        # Inner white circle (Donut hole)
        self.canv.setFillColor(colors.white)
        self.canv.circle(cx, cy, inner_radius, fill=1, stroke=0)
        
        # Center Value
        self.canv.setFillColor(HexColor('#0f172a'))
        self.canv.setFont('Helvetica-Bold', 9)
        self.canv.drawCentredString(cx, cy - 3, f"{self.percentage:.0f}%")
        
        # Bottom Label
        if self.label:
            self.canv.setFont('Helvetica', 8)
            self.canv.setFillColor(HexColor('#64748b'))
            self.canv.drawCentredString(cx, 0, self.label)


def generate_pdf_report(claim: str, a1_result: dict, a2_result: dict, aep: dict) -> str:
    """Generate a professional PDF report with visual elements."""
    
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(reports_dir, f"moveh_report_{timestamp}.pdf")
    
    try:
        # Create document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Colors
        DARK = colors.HexColor('#0f172a')
        GRAY_700 = colors.HexColor('#334155')
        GRAY_600 = colors.HexColor('#475569')
        GRAY_500 = colors.HexColor('#64748b')
        GRAY_200 = colors.HexColor('#e2e8f0')
        GRAY_50 = colors.HexColor('#f8fafc')
        BLUE = colors.HexColor('#3b82f6')
        GREEN = colors.HexColor('#10b981')
        RED = colors.HexColor('#ef4444')
        AMBER = colors.HexColor('#f59e0b')
        WHITE = colors.white
        
        # Get verdict data
        verdict_data = aep.get("verdict", {})
        truth_prob = verdict_data.get("truth_probability", 50)
        
        if truth_prob >= 60:
            verdict_bg = colors.HexColor('#059669')
            stamp_text = "TRUE"
            gauge_pct = truth_prob
        elif truth_prob <= 40:
            verdict_bg = colors.HexColor('#dc2626')
            stamp_text = "FALSE"
            gauge_pct = 100 - truth_prob
        else:
            verdict_bg = colors.HexColor('#d97706')
            stamp_text = "UNCERTAIN"
            gauge_pct = 50
        
        content = []
        
        # ═══════════════════════════════════════════════════════════════
        # 1. VERDICT HERO SECTION
        # ═══════════════════════════════════════════════════════════════
        
        gauge = ConfidenceGauge(gauge_pct, WHITE, width=80, height=45)
        
        hero_content = [
            [gauge],
            [Paragraph(f"{stamp_text}", ParagraphStyle(
                'Stamp', fontSize=28, textColor=WHITE, fontName='Helvetica-Bold', 
                alignment=TA_CENTER, leading=32, spaceBefore=2
            ))],
            [Paragraph(f"{gauge_pct:.0f}% confidence", ParagraphStyle(
                'Sub', fontSize=10, textColor=WHITE, alignment=TA_CENTER
            ))]
        ]
        
        hero_table = RLTable(hero_content, colWidths=[doc.width])
        hero_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), verdict_bg),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ]))
        content.append(hero_table)
        content.append(Spacer(1, 15))
        
        # Header Info
        header_row = [[
            Paragraph("MOVEH", ParagraphStyle('Logo', fontSize=10, textColor=GRAY_600, fontName='Helvetica-Bold')),
            Paragraph(f"{datetime.now().strftime('%B %d, %Y')}", ParagraphStyle('Date', fontSize=10, textColor=GRAY_500, alignment=TA_RIGHT))
        ]]
        content.append(RLTable(header_row, colWidths=[doc.width/2, doc.width/2]))
        content.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=15))
        
        # ═══════════════════════════════════════════════════════════════
        # 2. CLAIM vs REALITY
        # ═══════════════════════════════════════════════════════════════
        
        reasoning = aep.get("reasoning", "Analysis in progress...")
        claim_short = claim[:200] + "..." if len(claim) > 200 else claim
        
        style_rumor = ParagraphStyle('Rumor', fontSize=11, leading=15, textColor=GRAY_700)
        style_reality = ParagraphStyle('Reality', fontSize=10, leading=14, textColor=GRAY_600)
        
        rumor_content = [
            [Paragraph("THE CLAIM", ParagraphStyle('H1', fontSize=8, textColor=GRAY_500))],
            [Paragraph(f'"{claim_short}"', style_rumor)]
        ]
        
        reality_content = [
            [Paragraph("THE REALITY", ParagraphStyle('H2', fontSize=8, textColor=BLUE))],
            [Paragraph(str(reasoning), style_reality)]
        ]
        
        col_w = doc.width * 0.48
        
        t_rumor = RLTable(rumor_content, colWidths=[col_w - 12])
        t_rumor.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, GRAY_200),
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        t_reality = RLTable(reality_content, colWidths=[col_w - 12])
        t_reality.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, GRAY_200),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        main_claim_table = RLTable([[t_rumor, t_reality]], colWidths=[col_w, col_w])
        main_claim_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        content.append(main_claim_table)
        content.append(Spacer(1, 20))

        # ═══════════════════════════════════════════════════════════════
        # 3. METRICS - SIMPLIFIED (no custom flowables that may cause issues)
        # ═══════════════════════════════════════════════════════════════
        
        integrity = a2_result.get("integrity_score", 0) * 100
        ai_prob = a2_result.get("detection_summary", {}).get("ai_probability", 0) * 100
        sources_count = sum(len(sr.get("results", [])) for sr in a1_result.get("search_results", []) if isinstance(sr, dict))
        red_flags = len(a2_result.get("penalties_applied", []))

        # Simple text-based metrics (more reliable than custom flowables)
        int_color = GREEN if integrity >= 70 else (AMBER if integrity >= 40 else RED)
        ai_color = RED if ai_prob >= 70 else (AMBER if ai_prob >= 40 else GREEN)
        
        metrics_row = [[
            Paragraph(f"<b>🛡️ Integrity</b><br/><font size='14' color='{int_color.hexval()}'>{integrity:.0f}%</font>", 
                ParagraphStyle('M1', fontSize=8, alignment=TA_CENTER, leading=16)),
            Paragraph(f"<b>🤖 AI Prob</b><br/><font size='14' color='{ai_color.hexval()}'>{ai_prob:.0f}%</font>", 
                ParagraphStyle('M2', fontSize=8, alignment=TA_CENTER, leading=16)),
            Paragraph(f"<b>🔗 Sources</b><br/><font size='14'>{sources_count}</font>", 
                ParagraphStyle('M3', fontSize=8, alignment=TA_CENTER, leading=16)),
            Paragraph(f"<b>🚩 Red Flags</b><br/><font size='14' color='#ef4444'>{red_flags}</font>", 
                ParagraphStyle('M4', fontSize=8, alignment=TA_CENTER, leading=16)),
        ]]
        
        metrics_table = RLTable(metrics_row, colWidths=[doc.width/4]*4)
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, WHITE),
        ]))
        content.append(metrics_table)
        content.append(Spacer(1, 20))

        # ═══════════════════════════════════════════════════════════════
        # 3.5 CHAIN METADATA (NEW)
        # ═══════════════════════════════════════════════════════════════
        
        chain_meta = aep.get("chain_metadata", {})
        keywords = chain_meta.get("keywords", [])
        claim_type_name = chain_meta.get("claim_type_name", "UNKNOWN")
        freshness_hours = chain_meta.get("freshness_hours", 0)
        claim_hash_short = chain_meta.get("claim_hash", "N/A")[:16] + "..."
        
        # Format freshness
        if freshness_hours == 0:
            freshness_text = "Never expires"
            freshness_color = GREEN
        elif freshness_hours <= 24:
            freshness_text = f"{freshness_hours} hours"
            freshness_color = RED
        else:
            freshness_text = f"{freshness_hours // 24} days"
            freshness_color = AMBER
        
        content.append(Paragraph("ON-CHAIN METADATA", ParagraphStyle('ChainHead', fontSize=10, fontName='Helvetica-Bold', spaceAfter=8, textColor=GRAY_700)))
        
        chain_data = [
            ["Keywords", ", ".join(keywords) if keywords else "N/A"],
            ["Claim Type", claim_type_name],
            ["Freshness", freshness_text],
            ["Claim Hash", claim_hash_short],
        ]
        
        chain_table = RLTable(chain_data, colWidths=[doc.width * 0.25, doc.width * 0.75])
        chain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), GRAY_50),
            ('TEXTCOLOR', (0, 0), (0, -1), GRAY_600),
            ('TEXTCOLOR', (1, 0), (1, -1), GRAY_700),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_200),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        content.append(chain_table)
        content.append(Spacer(1, 20))

        # ═══════════════════════════════════════════════════════════════
        # 4. SOURCES & FLAGS
        # ═══════════════════════════════════════════════════════════════
        
        content.append(Paragraph("EVIDENCE & ANALYSIS", ParagraphStyle('Head', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10)))
        
        search_results = a1_result.get("search_results", [])
        
        # Create Cards
        for i, sr in enumerate(search_results):
            results_list = sr.get("results", []) if isinstance(sr, dict) else []
            for result in results_list:  # Show all sources
                if not isinstance(result, dict):
                    continue
                
                title = str(result.get("title", "Source"))[:80]
                url = str(result.get("url", ""))
                content_text = str(result.get("content", ""))[:150]
                
                try:
                    domain = url.split('/')[2].replace('www.', '') if len(url.split('/')) > 2 else "Web"
                except:
                    domain = "Web"
                
                # Badge Color
                badge_text = "SOURCE"
                badge_bg = GRAY_200
                badge_fg = GRAY_700
                if 'gov' in url: badge_text, badge_bg, badge_fg = "OFFICIAL", colors.HexColor('#dcfce7'), GREEN
                elif 'reuters' in url or 'apnews' in url: badge_text, badge_bg, badge_fg = "NEWS", colors.HexColor('#dbeafe'), BLUE

                # Source Card Layout
                card_content = [
                    [
                        Paragraph(f"<b>{title}</b>", ParagraphStyle('ST', fontSize=9)),
                        Paragraph(f"{badge_text}", ParagraphStyle('Badg', fontSize=6, backColor=badge_bg, textColor=badge_fg, alignment=TA_CENTER, borderPadding=2))
                    ],
                    [
                        Paragraph(f"<font color='#64748b'>{content_text}...</font>", ParagraphStyle('Snip', fontSize=8, leading=10)),
                        ""
                    ],
                    [
                        Paragraph(f"🔗 {domain}", ParagraphStyle('Dom', fontSize=7, textColor=BLUE)),
                        ""
                    ]
                ]
                
                # Adjusted column widths to prevent badge overlap (80% / 20%)
                card = RLTable(card_content, colWidths=[doc.width * 0.8, doc.width * 0.15])
                card.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.5, GRAY_200),
                    ('SPAN', (0, 1), (1, 1)),  # Span snippet across
                    ('SPAN', (0, 2), (1, 2)),  # Span domain across
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Right align badge
                ]))
                
                content.append(KeepTogether(card))  # Prevent page breaks inside card
                content.append(Spacer(1, 6))
        
        # Red Flags at bottom
        penalties = a2_result.get("penalties_applied", [])
        if penalties:
            content.append(Spacer(1, 10))
            content.append(Paragraph("Risk Indicators:", ParagraphStyle('Risk', fontSize=9, fontName='Helvetica-Bold')))
            
            flag_text = ""
            for name, score in penalties:
                flag_text += f'&nbsp;&nbsp;<font color="#ef4444">●</font> {name} '
                
            content.append(Paragraph(flag_text, ParagraphStyle('Flags', fontSize=9, textColor=GRAY_700, leading=14)))

        # Footer
        content.append(Spacer(1, 30))
        chain_meta = aep.get("chain_metadata", {})
        footer_text = f"Report ID: {aep.get('claim_id', 'N/A')} | Type: {chain_meta.get('claim_type_name', 'N/A')} | Generated via MoveH AI"
        content.append(Paragraph(footer_text, 
                                 ParagraphStyle('Foot', fontSize=7, textColor=GRAY_500, alignment=TA_CENTER)))

        doc.build(content)
        return pdf_path
    
    except Exception as e:
        # Fallback: Create a simple PDF if the fancy one fails
        logger.error(f"PDF generation error: {e}")
        
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        content = [
            Paragraph("MoveH Fact-Check Report", ParagraphStyle('Title', fontSize=24, spaceAfter=20)),
            Paragraph(f"Claim: {claim}", ParagraphStyle('Claim', fontSize=12, spaceAfter=10)),
            Paragraph(f"Verdict: {aep.get('verdict', {}).get('decision', 'UNKNOWN')}", ParagraphStyle('Verdict', fontSize=14, spaceAfter=10)),
            Paragraph(f"Reasoning: {aep.get('reasoning', 'N/A')}", ParagraphStyle('Reasoning', fontSize=10)),
        ]
        doc.build(content)
        return pdf_path


# ============ Shelby Storage Integration ============
def upload_to_shelby(pdf_path: str, expiry: str = "in 30 days") -> dict:
    """
    Upload PDF report to Shelby decentralized storage.
    
    Args:
        pdf_path: Path to the PDF file
        expiry: Expiration time (e.g., 'tomorrow', 'in 30 days', '2025-12-31')
    
    Returns:
        dict with upload status, explorer URL, etc.
    """
    # Check if Shelby CLI is installed
    if not shutil.which("shelby"):
        logger.warning("Shelby CLI not installed. Install with: npm i -g @shelby-protocol/cli")
        return {
            "success": False,
            "error": "Shelby CLI not installed",
            "install_cmd": "npm i -g @shelby-protocol/cli"
        }
    
    try:
        # Generate blob name from filename
        filename = os.path.basename(pdf_path)
        blob_name = f"moveh-reports/{filename}"
        
        # Upload to Shelby with auto-confirm
        cmd = [
            "shelby", "upload",
            pdf_path,
            blob_name,
            "-e", expiry,
            "--assume-yes"  # Auto-confirm payment
        ]
        
        logger.info(f"Uploading to Shelby: {blob_name}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            # Parse output for explorer URL
            output = result.stdout
            explorer_url = None
            
            # Try to extract Shelby Explorer URL from output
            for line in output.split("\n"):
                if "explorer.shelby.xyz" in line:
                    # Extract URL
                    import re
                    urls = re.findall(r'https://explorer\.shelby\.xyz/[^\s]+', line)
                    if urls:
                        explorer_url = urls[0]
                        break
            
            logger.info(f"Shelby upload successful: {blob_name}")
            return {
                "success": True,
                "blob_name": blob_name,
                "explorer_url": explorer_url,
                "expiry": expiry,
                "output": output
            }
        else:
            error_msg = result.stderr or result.stdout
            logger.error(f"Shelby upload failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except subprocess.TimeoutExpired:
        logger.error("Shelby upload timed out")
        return {"success": False, "error": "Upload timed out"}
    except Exception as e:
        logger.error(f"Shelby upload error: {e}")
        return {"success": False, "error": str(e)}


# ============ Main Pipeline ============
def run_truthchain(claim: str):
    """Run the full TruthChain pipeline with PARALLEL agent execution."""
    logger.info(f"Processing claim: {claim}")
    start_time = time.time()
    
    print_header()
    print_claim_box(claim)
    
    # ============ STEP 0: Check Blockchain for Existing Verdict ============
    console.print()
    console.print(Panel(
        "[bold blue]⛓️ Checking Blockchain for Cached Verdict[/bold blue]\n"
        "[dim]Searching for existing fact-checks on-chain...[/dim]",
        border_style="blue",
        padding=(0, 2)
    ))
    
    cached_verdict = None
    try:
        with console.status("[bold blue]⛓️ Searching blockchain...", spinner="dots"):
            cached_verdict = lookup_cached_verdict(claim)
    except Exception as e:
        logger.warning(f"Chain lookup failed: {e}")
        console.print(f"[dim]Chain lookup skipped: {e}[/dim]")
    
    if cached_verdict:
        # Found a cached verdict!
        if cached_verdict.is_fresh:
            console.print(Panel(
                f"[bold green]✅ CACHED VERDICT FOUND (Fresh)[/bold green]\n\n"
                f"[white]Verdict:[/white] [bold]{cached_verdict.verdict}[/bold]\n"
                f"[white]Confidence:[/white] {cached_verdict.confidence}%\n"
                f"[white]Relevance:[/white] {cached_verdict.relevance_score:.0%}\n"
                f"[white]Claim Hash:[/white] [cyan]{cached_verdict.claim_hash}[/cyan]\n"
                f"[white]Shelby CID:[/white] [dim]{cached_verdict.shelby_cid}[/dim]\n\n"
                f"[dim]Skipping agent pipeline - using cached result![/dim]",
                title="[green]⚡ Cache Hit[/green]",
                border_style="green",
                padding=(1, 2)
            ))
            
            elapsed_time = time.time() - start_time
            console.print(f"\n[dim]⚡ Lookup completed in {elapsed_time:.1f}s[/dim]")
            logger.info(f"Cache hit! Verdict: {cached_verdict.verdict}, Confidence: {cached_verdict.confidence}")
            
            # Return cached result as AEP-like structure
            return {
                "cached": True,
                "claim_hash": cached_verdict.claim_hash,
                "verdict": {
                    "decision": cached_verdict.verdict,
                    "truth_probability": cached_verdict.confidence,
                    "confidence_level": "CACHED",
                },
                "shelby_cid": cached_verdict.shelby_cid,
                "from_chain": True,
            }
        else:
            console.print(Panel(
                f"[bold yellow]⚠️ STALE VERDICT FOUND[/bold yellow]\n\n"
                f"[white]Previous Verdict:[/white] {cached_verdict.verdict}\n"
                f"[white]Claim Hash:[/white] [dim]{cached_verdict.claim_hash}[/dim]\n\n"
                f"[dim]Verdict has expired - running fresh verification...[/dim]",
                title="[yellow]🔄 Re-verification Needed[/yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))
            logger.info(f"Stale verdict found, re-verifying: {cached_verdict.claim_hash}")
    else:
        console.print("[dim]No cached verdict found - running full verification...[/dim]")
    
    # ============ PARALLEL: Agent 1 + Agent 2 ============
    console.print()
    console.print(Panel(
        "[bold cyan]⚡ Running Agent 1 & Agent 2 in PARALLEL[/bold cyan]\n"
        "[dim]• Fact Checker: Searching web for evidence...\n"
        "• Forensic Expert: Analyzing linguistic patterns...[/dim]",
        border_style="cyan",
        padding=(0, 2)
    ))
    
    logger.info("Starting Agent 1 & Agent 2 in parallel")
    
    # Initialize agents
    fact_checker = FactChecker()
    forensic_expert = ForensicExpert()
    
    a1_result = None
    a2_result = None
    
    # Run both agents in parallel using ThreadPoolExecutor
    with console.status("[bold cyan]⚡ Parallel Analysis: Fact Checker + Forensic Expert...", spinner="dots"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            future_a1 = executor.submit(fact_checker.verify_claim, claim)
            future_a2 = executor.submit(forensic_expert.analyze_text, claim)
            
            # Wait for both to complete
            a1_result = future_a1.result()
            a2_result = future_a2.result()
    
    parallel_time = time.time() - start_time
    logger.info(f"Parallel execution complete in {parallel_time:.1f}s")
    
    # Display Agent 1 results
    print_agent_header(1, "Agent 1: The Fact Checker", "🔍", "blue")
    logger.info(f"Agent 1 complete: {a1_result.get('preliminary_verdict', 'N/A')}")
    print_fact_checker_results(a1_result)
    
    # Display Agent 2 results
    print_agent_header(2, "Agent 2: The Forensic Expert", "🕵️", "magenta")
    logger.info(f"Agent 2 complete: Score {a2_result.get('integrity_score', 0):.2f}")
    print_forensic_results(a2_result)
    
    # ============ Agent 3: The Judge ============
    print_agent_header(3, "Agent 3: The Judge", "⚖️", "yellow")
    console.print("[dim]Synthesizing evidence and rendering verdict...[/dim]")
    
    logger.info("Starting Agent 3: The Judge")
    judge = TheJudge()
    
    with console.status("[bold yellow]⚖️ The Judge: Deliberating...", spinner="dots"):
        aep = judge.adjudicate(a1_result, a2_result)
    
    logger.info(f"Agent 3 complete: {aep.get('verdict', {}).get('decision', 'N/A')}")
    print_judge_results(aep)
    
    # ============ PARALLEL: PDF Generation + Shelby Upload Prep ============
    console.print()
    
    pdf_path = None
    shelby_result = None
    
    with console.status("[bold cyan]📄 Generating PDF Report...", spinner="dots"):
        pdf_path = generate_pdf_report(claim, a1_result, a2_result, aep)
    
    logger.info(f"PDF report generated: {pdf_path}")
    
    # Upload to Shelby in background (non-blocking)
    if shutil.which("shelby"):
        def upload_async():
            return upload_to_shelby(pdf_path, expiry="in 30 days")
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            shelby_future = executor.submit(upload_async)
            
            # Show quick status while uploading
            with console.status("[bold magenta]☁️ Uploading to Shelby...", spinner="dots"):
                shelby_result = shelby_future.result(timeout=30)
        
        if shelby_result and shelby_result.get("success"):
            logger.info(f"Shelby upload successful: {shelby_result.get('blob_name')}")
        else:
            logger.warning(f"Shelby upload skipped: {shelby_result.get('error', 'Unknown error') if shelby_result else 'Timeout'}")
    
    # ============ Submit to Aptos Blockchain ============
    aptos_tx_hash = None
    chain_metadata = aep.get("chain_metadata", {})
    verdict_decision = aep.get("verdict", {}).get("decision", "UNCERTAIN")
    confidence_score = int(aep.get("verdict", {}).get("truth_probability", 50))
    shelby_cid = shelby_result.get("blob_name", "") if shelby_result and shelby_result.get("success") else ""
    
    if chain_metadata.get("claim_hash"):
        with console.status("[bold blue]⛓️ Submitting to Aptos Blockchain...", spinner="dots"):
            try:
                aptos_tx_hash = submit_verdict_to_chain(
                    chain_metadata=chain_metadata,
                    shelby_cid=shelby_cid,
                    verdict=verdict_decision,
                    confidence=confidence_score,
                )
                if aptos_tx_hash:
                    logger.info(f"Aptos submission successful: {aptos_tx_hash}")
                    # Update AEP with transaction hash
                    aep["storage"]["aptos_tx"] = aptos_tx_hash
                else:
                    logger.warning("Aptos submission failed - no transaction hash returned")
            except Exception as e:
                logger.error(f"Aptos submission error: {e}")
    
    # ============ Summary ============
    elapsed_time = time.time() - start_time
    
    verdict_data = aep.get("verdict", {})
    truth_prob = verdict_data.get("truth_probability", 50)
    
    if truth_prob >= 60:
        color, icon = "green", "✅"
        verdict_display = f"{truth_prob:.0f}% likely TRUE"
    elif truth_prob <= 40:
        color, icon = "red", "❌"
        verdict_display = f"{100-truth_prob:.0f}% likely FALSE"
    else:
        color, icon = "yellow", "⚠️"
        verdict_display = f"Uncertain ({truth_prob:.0f}%)"
    
    # Build summary text with performance metrics
    summary_text = (
        f"[bold white]Analysis Complete[/bold white]\n\n"
        f"Verdict: [bold {color}]{icon} {verdict_display}[/bold {color}]\n"
        f"⚡ Total Time: [cyan]{elapsed_time:.1f}s[/cyan] [dim](parallel mode)[/dim]\n\n"
        f"[bold]📄 PDF Report:[/bold] [link=file://{pdf_path}]{pdf_path}[/link]\n"
    )
    
    # Add Shelby info if uploaded
    if shelby_result and shelby_result.get("success"):
        explorer_url = shelby_result.get("explorer_url", "")
        summary_text += f"[bold]☁️ Shelby:[/bold] [link={explorer_url}]{shelby_result.get('blob_name')}[/link]\n"
    
    # Add Aptos blockchain info if submitted
    if aptos_tx_hash:
        aptos_explorer = f"https://explorer.aptoslabs.com/txn/{aptos_tx_hash}?network=testnet"
        summary_text += f"[bold]⛓️ Aptos:[/bold] [link={aptos_explorer}]{aptos_tx_hash[:16]}...[/link]\n"
    
    summary_text += f"[dim]Log File: {log_file}[/dim]"
    
    console.print()
    console.print(Panel(
        summary_text,
        title="[bold green]⚡ Summary (Optimized)[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    
    # Open PDF automatically on macOS
    if sys.platform == "darwin":
        os.system(f'open "{pdf_path}"')
    
    logger.info(f"Pipeline complete in {elapsed_time:.1f}s")
    logger.info(f"Final verdict: {verdict_display}")
    
    return aep


def interactive_mode():
    """Run in interactive mode with multiple claims."""
    print_header()
    
    console.print(Panel(
        "[bold white]Interactive Mode[/bold white]\n\n"
        "Enter claims to verify. Type [cyan]'quit'[/cyan] or [cyan]'exit'[/cyan] to stop.\n"
        "Type [cyan]'demo'[/cyan] for a sample claim.",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    demo_claims = [
        "Tesla announced they are acquiring Twitter for $100 billion",
        "URGENT!!! Amazon is bank curpted! CLICK HERE NOW to save your account!",
        "Apple Inc. reported Q4 2025 earnings of $1.95 per share, exceeding analyst expectations.",
        "Breaking: Bitcoin will reach $1 million by tomorrow according to insider sources!"
    ]
    
    while True:
        console.print()
        claim = console.input("[bold cyan]📝 Enter claim to verify:[/bold cyan] ").strip()
        
        if claim.lower() in ['quit', 'exit', 'q']:
            console.print("\n[bold green]👋 Goodbye![/bold green]\n")
            break
        
        if claim.lower() == 'demo':
            import random
            claim = random.choice(demo_claims)
            console.print(f"[dim]Using demo claim: {claim}[/dim]")
        
        if not claim:
            console.print("[yellow]Please enter a claim to verify.[/yellow]")
            continue
        
        # Validate input is a claim, not a question
        is_valid, error_msg = validate_claim(claim)
        if not is_valid:
            console.print(error_msg)
            continue
        
        try:
            run_truthchain(claim)
        except Exception as e:
            logger.error(f"Error processing claim: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Check log file for details.[/dim]")


# ============ Entry Point ============
if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # Command line argument mode
            claim = " ".join(sys.argv[1:])
            
            # Validate input
            is_valid, error_msg = validate_claim(claim)
            if not is_valid:
                console.print(error_msg)
                sys.exit(1)
            
            run_truthchain(claim)
        else:
            # Interactive mode
            interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Interrupted by user[/bold yellow]")
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        console.print(f"[bold red]Fatal error: {e}[/bold red]")
        console.print(f"[dim]Log file: {log_file}[/dim]")
        sys.exit(1)
