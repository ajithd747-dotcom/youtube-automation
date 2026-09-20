"""Shot DSL constants shared by the director (plain Python) and scene_lib (inside Blender). No bpy here."""
ICONS = ["star", "heart", "arrow_right", "check", "cross", "bolt", "lightbulb", "coin", "laptop", "phone", "chart_up",
         "chart_bar", "clock", "globe", "question", "exclaim", "lock", "gear", "tree", "house", "sun", "cloud"]
SHAPES = ["cube", "sphere", "cylinder", "cone", "torus", "rect"]
ACTIONS = ["idle", "walk", "run", "wave", "jump", "celebrate", "think", "point", "talk", "sad"]
ENTRIES = ["pop_in", "slide_in_left", "slide_in_right", "slide_in_top", "slide_in_bottom", "none"]
LOOPS = ["none", "float", "bounce", "spin", "roll", "sway", "pulse", "shake"]
CAMERAS = ["static", "push_in", "pull_out", "pan_left", "pan_right", "orbit"]
STYLES = ["stickman", "kinetic", "3d"]
TYPES = ["text", "stickman", "icon", "ground"] + SHAPES

STYLES = STYLES + ["cinematic"]
MOODS = ["day", "sunset", "night", "studio", "neon"]
# cinematic recipes: name -> (default mood, what it shows). Keep in sync with cine_recipes.py (checked at import there).
RECIPES = {
    "robot_intro": ("sunset", "3D robot waves hello on a glossy floor with a floating glowing title (hook, greeting, introducing someone)"),
    "workshop_walk": ("studio", "robot walks across a moody workshop with lamps, crates and light shafts (travelling, morning routine, working, journey)"),
    "glass_showcase": ("studio", "rotating glass sphere, gold ring, chrome ball and glowing crystal on a mirror floor (treasures, products, polishing, details, beauty)"),
    "domino_run": ("sunset", "long winding line of colourful dominoes toppling in a chain reaction (chain reaction, momentum, cause and effect, one small push)"),
    "crate_smash": ("sunset", "heavy steel ball smashes a wall of wooden crates, debris tumbles in slow motion (destruction, impact, climax, crash, collapse)"),
    "cloth_banner": ("day", "big striped banner rippling on a flagpole in the wind under a blue sky (victory, flag, wind, success, pride)"),
    "fireworks": ("night", "fireworks bursting over a dark reflective lake with glowing sparks (celebration, night sky, finale, wonder)"),
    "jelly_pit": ("neon", "translucent jelly blobs wobble while colourful balls rain into a pile under neon light (fun, bounce, party, play, energy)"),
    "campfire_smoke": ("night", "a crackling campfire with real simulated fire and rising smoke, flickering warm light and embers (warmth, night, rest, story, survival, fire)"),
    "water_splash": ("studio", "drops falling into a pool with a glassy, refractive liquid splash in slow motion (water, rain, splash, drink, ocean, calm, liquid)"),
    "fuzzy_creature": ("day", "a soft furry creature with thousands of hair strands bouncing in a breeze (fur, hair, cute, pet, animal, soft, fluffy)"),
    "finale_confetti": ("night", "robot cheers under a glowing title while confetti rains down (ending, thanks, outro, celebration, call to action)"),
}
