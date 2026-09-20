# PAPER HEART — character design sheet

Taken from the two reference images supplied 2026-09-20. **Drop the image files themselves into
`reference/` as `girl.jpg` and `man.jpg`** — they arrived through chat, so they exist in the
conversation but not on disk, and this sheet is the part that actually drives the build:
model search terms, toon ramp colours, and the shader values in `script.md` §8.

Two things in the references line up with the script almost exactly, and both are worth keeping:

- **He is on the phone in the reference.** That is the whole of Act 1 and the thing he gives up
  in S46. The pose in the reference is very close to S11.
- **Her reference background is a twilight city — deep blue above, warm band at the horizon,
  stars coming out.** That is the Act 6 palette already, and close to what is rendering now.

---

## THE GIRL — the exam candidate

Wistful, looking up and back over her shoulder. Soft, tired, not glamorous. The reference has
her lit from behind by a sunset, warm rim on every edge of the hair — worth reproducing as her
standing rim light from Act 4 onward.

| Feature | Description |
| --- | --- |
| Hair | Long, past mid-back, softly wavy. Near-black with a cool blue undertone, not flat black. Side-swept with loose strands across the face. Strong warm rim light picking out the silhouette |
| Hair accessory | **Silver star clip** above her left ear, small sparkle accents around it. A **dusty-rose ribbon** at the back |
| Eyes | Large, soft blue-grey. Bright highlight, visible lower-lid catch |
| Expression | Lips slightly parted, brows faintly raised. Melancholy rather than sad. Light blush across the nose |
| Top | Cream/white camisole, thin strap |
| Jacket | Oversized coral / peach shirt-jacket worn **off one shoulder** |
| Accessory | Dark shoulder bag strap across the chest with a small **teal round charm** |
| Build | Slight, 1.62 m |

**Palette**

| Part | Base | Shadow (hue-shifted, never just darker) | Light |
| --- | --- | --- | --- |
| Hair | `#1A1620` | `#221E2E` | `#3E3646` |
| Hair rim (sunset) | `#F2A98A` | — | `#FFD0B4` |
| Eyes | `#7FA8C9` | `#5C7F9E` | `#BBD9EE` |
| Skin | `#F5D9C4` | `#D9A899` | `#FFF0E2` |
| Jacket | `#E8A08A` | `#C07A66` | `#F7C0AC` |
| Camisole | `#F5F0E8` | `#D8CFC4` | `#FFFFFF` |
| Ribbon | `#C98BA0` | `#A66A80` | — |
| Bag charm | `#2AA8A0` | `#1B7A74` | `#5FD6CE` |

**Why she works for this film:** the reference already reads as someone carrying something.
Keep that. She should not look cute-and-happy in Acts 1–2 — the reference expression *is* the
Act 2 expression.

---

## THE MAN — the one waiting on the call

White spiky hair, bright cyan eyes, black shirt with an undone tie, black gloves, phone to his
ear, half-smiling. Confident and sharp where she is soft.

| Feature | Description |
| --- | --- |
| Hair | Short, spiky, messy. White / very pale silver. Fringe falling across one eye |
| Eyes | Bright cyan-teal, high saturation. **The single most distinctive thing about him** — keep it loud, it is what pairs against her muted blue-grey |
| Expression | Slight confident smile, eyes lowered. Not smug — occupied |
| Top | Black ribbed sweater/shirt, open at the neck, collarbone visible, long sleeves |
| Tie | Black, hanging **undone** — sells "end of a long working day" without a word |
| Gloves | Black leather, both hands, slight specular |
| Lower | Dark trousers, black belt |
| Build | Tall, lean, 1.80 m |

**Palette**

| Part | Base | Shadow | Light |
| --- | --- | --- | --- |
| Hair | `#EDEDF2` | `#C3C4D0` (cool) | `#FFFFFF` |
| Eyes | `#35C5D4` | `#1E93A6` | `#9BEAF2` |
| Skin | `#F2DCC9` | `#D4A899` | `#FFF2E6` |
| Sweater | `#1C1C22` | `#121216` | `#33333D` |
| Tie | `#15151A` | `#0D0D10` | `#2A2A33` |
| Gloves | `#1A1A1F` | `#101014` | `#3A3A45` (specular band) |

**One thing you should know:** the male reference is recognisably **Gojo Satoru from Jujutsu
Kaisen** (fan art) — the white spiky hair plus bright blue-cyan eyes is his design. You said
you are not publishing, so for practice this is a non-issue; it only matters if that changes.
It is also *useful*: it makes the model much easier to find, because plenty of VRM/VRChat
avatars of that archetype exist.

---

## How this drives the build

### Model search terms

| For | Search on BOOTH / Sketchfab / VRoid Hub |
| --- | --- |
| Girl | `VRM 黒髪 ロング` (black long hair), `anime girl VRM long black hair`, `VRoid 女性 ロングヘア` |
| Man | `VRM 白髪 男性` (white hair male), `Gojo VRM`, `anime male VRM white hair`, `VRChat 男性アバター 白髪` |

If you build in VRoid Studio instead, both designs are well inside what it does out of the box —
her long wavy black hair and his short spiky white hair are both preset hair types, and the
palettes above are the exact values to type into the colour pickers.

### Colour contrast — the reason this pairing works on screen

Their palettes are near-opposites, which is doing real work for the film:

- **Hair:** her near-black vs his near-white. In the S43 white void and the Act 6 silhouettes
  they will read instantly apart with no faces visible at all.
- **Eyes:** her muted blue-grey `#7FA8C9` vs his saturated cyan `#35C5D4`. Same hue family,
  opposite saturation. In S38/S39 — the two matched push-ins — that contrast is what carries
  the cut without dialogue.
- **Costume:** her warm coral vs his cold black. **This is already the two-world colour script
  in §3.** He is his palette; she is hers. When the palettes converge at the meeting, the
  characters are literally what converge.

That last point is lucky and worth protecting: do not warm him up or cool her down before the
crossing.

### Rim light

Her reference is backlit with a warm sunset rim on every hair edge. Make that her standing
treatment from Act 4 onward (§8 already calls for a rim on every shot from Act 4). For him,
the reference is lit by a cold window — keep his rim cool and white through Acts 1 and 3, and
warm it to `#FFD9A0` at the contact, in the same 10-frame shift as S47.
