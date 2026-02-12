#!/usr/bin/env python3
"""Learn the 8amEST + ControllerFX strategy from all available content."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hl_bot.services.strategy_learner import StrategyLearner


async def main():
    print("=" * 60)
    print("STRATEGY LEARNING ENGINE")
    print("Building deep understanding from all content sources")
    print("=" * 60)
    
    learner = StrategyLearner(
        knowledge_dir=Path("/opt/swarmops/projects/hl-bot-v2/knowledge")
    )
    
    # === LEARN FROM YOUTUBE TRANSCRIPTS ===
    print("\n[1/4] Learning from YouTube course transcripts...")
    
    transcript_path = Path("/tmp/course_analysis/full_course.txt")
    if transcript_path.exists():
        content = transcript_path.read_text()
        print(f"  - Loaded {len(content)} chars from 8amEST course")
        await learner.learn_from_content(
            content=content,
            source_name="8amEST Price Action Course (YouTube)",
            content_type="transcript"
        )
        print("  ✓ Learned from YouTube course")
    else:
        print("  ✗ Transcript not found")
    
    # === LEARN FROM PDF ANALYSIS ===
    print("\n[2/4] Learning from ControllerFX Playbook analysis...")
    
    pdf_analysis_path = Path("/home/motbot/clawd/inbox/PLAYBOOK_1_ANALYSIS.md")
    if pdf_analysis_path.exists():
        content = pdf_analysis_path.read_text()
        print(f"  - Loaded {len(content)} chars from playbook analysis")
        await learner.learn_from_content(
            content=content,
            source_name="ControllerFX Playbook 2022 (PDF)",
            content_type="pdf_text"
        )
        print("  ✓ Learned from PDF playbook")
    else:
        print("  ✗ PDF analysis not found")
    
    # === LEARN FROM CHART IMAGES ===
    print("\n[3/4] Learning visual patterns from chart examples...")
    
    chart_dir = Path("/tmp/playbook_pages")
    if chart_dir.exists():
        # Learn from key pages with setup diagrams
        key_pages = [
            "page-01.png",  # Overview with all setups
            "page-13.png",  # Breakout entry
            "page-15.png",  # Celery play
            "page-17.png",  # Onion play
            "page-20.png",  # Breakout small wick
            "page-22.png",  # Breakout steeper wick
            "page-28.png",  # Fakeout small wick
            "page-30.png",  # Fakeout steeper wick
            "page-36.png",  # Onion small wick
        ]
        
        for page_name in key_pages:
            page_path = chart_dir / page_name
            if page_path.exists():
                print(f"  - Analyzing {page_name}...")
                try:
                    img_bytes = page_path.read_bytes()
                    result = await learner.learn_from_image(img_bytes, page_name)
                    print(f"    ✓ Learned: {result.get('setup_type', 'pattern')}")
                except Exception as e:
                    print(f"    ✗ Error: {e}")
    else:
        print("  ✗ Chart images not found")
    
    # === GENERATE DETECTION CODE ===
    print("\n[4/4] Generating detection code from learned knowledge...")
    
    try:
        code = await learner.generate_detection_code()
        
        # Save code to file
        code_path = Path("/opt/swarmops/projects/hl-bot-v2/backend/src/hl_bot/services/learned_detector.py")
        code_path.write_text(code)
        print(f"  ✓ Generated {len(code)} chars of detection code")
        print(f"  ✓ Saved to: {code_path}")
    except Exception as e:
        print(f"  ✗ Code generation failed: {e}")
    
    # === SUMMARY ===
    print("\n" + "=" * 60)
    print("LEARNING COMPLETE")
    print("=" * 60)
    
    knowledge = learner._current_knowledge
    if knowledge:
        print(f"\nStrategy: {knowledge.name}")
        print(f"Sources: {', '.join(knowledge.sources)}")
        print(f"Concepts learned: {len(knowledge.concepts)}")
        print(f"\nPhilosophy:")
        print(f"  {knowledge.philosophy[:200]}...")
        print(f"\nConcepts:")
        for name, concept in list(knowledge.concepts.items())[:10]:
            print(f"  - {name} ({concept.category})")
        print(f"\nWorkflow steps: {len(knowledge.workflow_steps)}")
        print(f"Code generated: {'Yes' if knowledge.detection_code else 'No'}")
    
    print("\n✓ Strategy understanding complete!")
    print("The bot now deeply understands the 8amEST + ControllerFX methodology.")


if __name__ == "__main__":
    asyncio.run(main())
