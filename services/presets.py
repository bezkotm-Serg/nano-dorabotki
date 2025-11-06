from typing import List, Tuple

def build_presets() -> List[Tuple[str, str, str]]:
    """
    Возвращает список (scene, shot, prompt).
    Порядок важен: сначала 1..7 сцен, внутри — дальний/средний/крупный.
    """
    presets: List[Tuple[str, str, str]] = []

    # 1. Бутик / Showroom
    presets += [
        ("Бутик / Showroom", "Дальний план",
         "full-body fashion photo, model standing confidently inside a luxury boutique, surrounded by clothing racks and soft spotlights, elegant mirror reflections, polished marble floor, cinematic composition, editorial style, natural posing, high-end fashion campaign look"),
        ("Бутик / Showroom", "Средний план",
         "half-body shot, focus on outfit details and silhouette, boutique background softly blurred, warm lighting on model’s face, subtle reflections in glass, refined editorial mood, balanced framing"),
        ("Бутик / Showroom", "Крупный план",
         "close-up of neckline and fabric texture, gold jewelry sparkle, blurred boutique shelves behind, shallow depth of field, glossy magazine aesthetic, ultra-detailed fabric texture"),
    ]

    # 2. Классическая гостиная / Интерьер
    presets += [
        ("Классическая гостиная / Интерьер", "Дальний план",
         "model posing in a spacious neoclassical living room with high ceilings, soft daylight through tall windows, neutral tones and elegant furniture, editorial look, clean perspective"),
        ("Классическая гостиная / Интерьер", "Средний план",
         "mid-shot near a vintage sofa or column, focus on outfit’s silhouette, natural light highlighting the waistline, gentle shadows adding depth, refined minimal style"),
        ("Классическая гостиная / Интерьер", "Крупный план",
         "close-up on buttons, cuffs or neckline, soft warm reflection from nearby lamp, creamy background blur, tactile fabric texture captured sharply"),
    ]

    # 3. Улица / Переход через улицу
    presets += [
        ("Улица / Переход через улицу", "Дальний план",
         "full-body outdoor fashion photo, model crossing city street in motion, modern architecture and cars blurred behind, strong natural sunlight, dynamic yet elegant pose"),
        ("Улица / Переход через улицу", "Средний план",
         "half-body shot at pedestrian crossing, breeze moving fabric slightly, confident expression, light bokeh from cars and buildings, stylish urban mood"),
        ("Улица / Переход через улицу", "Крупный план",
         "close-up of collar, lapel, or accessories, city reflections in sunglasses or jewelry, cinematic contrast lighting, crisp texture of suiting fabric"),
    ]

    # 4. Индустриальный лофт
    presets += [
        ("Индустриальный лофт", "Дальний план",
         "model standing in spacious industrial loft, exposed brick walls and large windows, fashion editorial setup with soft daylight, minimalist props, artistic composition"),
        ("Индустриальный лофт", "Средний план",
         "waist-up shot near window or column, warm sunlight highlighting face and outfit contours, contrast of textures (fabric vs. brick), modern creative feel"),
        ("Индустриальный лофт", "Крупный план",
         "close-up of details — stitching, buttons, fabric folds — warm golden light, soft focus on background metal structures, tactile depth and realism"),
    ]

    # 5. Hotel Lobby / Luxury Hall
    presets += [
        ("Hotel Lobby / Luxury Hall", "Дальний план",
         "full-body editorial fashion photo, model walking through a luxury hotel lobby with marble floors and chandeliers, warm golden ambient light, elegant interior perspective, cinematic composition, reflections on polished surfaces"),
        ("Hotel Lobby / Luxury Hall", "Средний план",
         "half-body portrait near elevator or marble column, warm soft lighting emphasizing the outfit silhouette, bokeh from chandeliers in background, poised confident pose, fashion campaign feel"),
        ("Hotel Lobby / Luxury Hall", "Крупный план",
         "close-up of neckline, jewelry, or fabric texture, background of blurred chandeliers, warm reflections on skin and metal details, glossy high-end magazine aesthetic"),
    ]

    # 6. Rooftop / City View Terrace
    presets += [
        ("Rooftop / City View Terrace", "Дальний план",
         "full-body shot on rooftop terrace overlooking the city skyline, golden-hour light, wind in fabric and hair, cinematic horizon, sense of sophistication and independence"),
        ("Rooftop / City View Terrace", "Средний план",
         "waist-up shot with cityscape bokeh behind, sunset tones on skin and fabric, confident expression, subtle breeze moving the jacket, elevated mood"),
        ("Rooftop / City View Terrace", "Крупный план",
         "close-up of lapel, earring, or hair movement against blurred skyline, warm sunlight reflections, crisp detail on texture, modern editorial tone"),
    ]

    # 7. Art Gallery / Minimal Space
    presets += [
        ("Art Gallery / Minimal Space", "Дальний план",
         "full-body minimalist shot in modern art gallery, neutral white walls, abstract paintings, soft even lighting, refined and clean aesthetic"),
        ("Art Gallery / Minimal Space", "Средний план",
         "mid-shot near sculpture or painting, focus on silhouette and clean lines, balanced symmetry, editorial calm tone"),
        ("Art Gallery / Minimal Space", "Крупный план",
         "close-up on fabric folds or accessory detail, soft museum lighting, gentle background blur, artistic yet luxurious atmosphere"),
    ]

    return presets