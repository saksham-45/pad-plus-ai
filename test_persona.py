"""Debug persona evolution phase"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import asyncio
from core.pipeline.context import PipelineContext
from core.pipeline.phases.persona_evolution import PersonaEvolutionPhase

async def test():
    # Fresh manager
    from memory.user_persona import get_user_persona_manager
    pm = get_user_persona_manager()

    # Create unique user per test run
    import uuid
    uid = f"test-{uuid.uuid4().hex[:6]}"
    up = pm.get_persona(uid)
    print(f"User {uid} before: verbosity={up.style_preferences['verbosity']}")

    phase = PersonaEvolutionPhase()
    ctx = PipelineContext(user_message="Spasibo!")
    ctx.context = {
        "experience_interaction_type": "praise",
        "experience_significance": 0.9,
        "user_id": uid,
    }
    result = await phase.execute(ctx)
    print(f"Phase result: success={result.success}")

    up2 = pm.get_persona(uid)
    print(f"User {uid} after:  verbosity={up2.style_preferences['verbosity']}")

    # Now test legacy fallback (no experience data)
    uid2 = f"test-legacy-{uuid.uuid4().hex[:6]}"
    up_leg = pm.get_persona(uid2)
    print(f"\nUser {uid2} before legacy: verbosity={up_leg.style_preferences['verbosity']}")

    ctx2 = PipelineContext(user_message="Spasibo, otlichno pomog!")
    ctx2.context = {"user_id": uid2}
    result2 = await phase.execute(ctx2)
    print(f"Phase result legacy: success={result2.success}")

    up_leg2 = pm.get_persona(uid2)
    print(f"User {uid2} after legacy:  verbosity={up_leg2.style_preferences['verbosity']}")

asyncio.run(test())
