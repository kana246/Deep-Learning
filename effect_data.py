# effect_data.py (または item_data.py に追記)

effects = {
    "speed": {
        "name": "移動速度上昇",
        "desc": "移動速度が上昇する。",
        "category": "エフェクト",
        "aliases": ["移動速度上昇", "スピード", "足が速くなる", "加速", "speed"],
        "id": {"Java版": "speed", "統合版": "speed"}
    },
    "slowness": {
        "name": "移動速度低下",
        "desc": "移動速度が低下する。",
        "category": "エフェクト",
        "aliases": ["移動速度低下", "鈍化", "のろま", "遅くなる", "slowness"],
        "id": {"Java版": "slowness", "統合版": "slowness"}
    },
    "haste": {
        "name": "採掘速度上昇",
        "desc": "採掘・攻撃速度が上昇する。",
        "category": "エフェクト",
        "aliases": ["採掘速度上昇", "効率", "ヘイスト", "早く掘る", "haste"],
        "id": {"Java版": "haste", "統合版": "haste"}
    },
    "mining_fatigue": {
        "name": "採掘速度低下",
        "desc": "採掘・攻撃速度が低下する。",
        "category": "エフェクト",
        "aliases": ["採掘速度低下", "疲労", "掘るのが遅くなる", "mining_fatigue"],
        "id": {"Java版": "mining_fatigue", "統合版": "mining_fatigue"}
    },
    "strength": {
        "name": "攻撃力上昇",
        "desc": "近接攻撃の攻撃力が上昇する。",
        "category": "エフェクト",
        "aliases": ["攻撃力上昇", "力", "強くなる", "パワー", "strength"],
        "id": {"Java版": "strength", "統合版": "strength"}
    },
    "instant_health": {
        "name": "即時回復",
        "desc": "体力を回復する（アンデッド系モブはダメージを受ける）。",
        "category": "エフェクト",
        "aliases": ["即時回復", "回復", "ヒール", "instant_health"],
        "id": {"Java版": "instant_health", "統合版": "instant_health"}
    },
    "instant_damage": {
        "name": "即時ダメージ",
        "desc": "ダメージを受ける（アンデッド系モブは体力を回復する）。",
        "category": "エフェクト",
        "aliases": ["即時ダメージ", "ダメージ", "攻撃", "instant_damage"],
        "id": {"Java版": "instant_damage", "統合版": "instant_damage"}
    },
    "jump_boost": {
        "name": "跳躍力上昇",
        "desc": "ジャンプ力が上昇し、落下ダメージが低下する。",
        "category": "エフェクト",
        "aliases": ["跳躍力上昇", "大ジャンプ", "高く飛ぶ", "jump_boost"],
        "id": {"Java版": "jump_boost", "統合版": "jump_boost"}
    },
    "nausea": {
        "name": "吐き気",
        "desc": "画面をゆがむ。",
        "category": "エフェクト",
        "aliases": ["吐き気", "めまい", "画面酔い", "nausea"],
        "id": {"Java版": "nausea", "統合版": "nausea"}
    },
    "regeneration": {
        "name": "再生能力",
        "desc": "時間経過とともに体力を回復する。",
        "category": "エフェクト",
        "aliases": ["再生能力", "リジェネ", "自動回復", "再生", "regeneration"],
        "id": {"Java版": "regeneration", "統合版": "regeneration"}
    },
    "resistance": {
        "name": "耐性",
        "desc": "受けるダメージが減少する（/kill、空腹、奈落を除く）。",
        "category": "エフェクト",
        "aliases": ["耐性", "防御", "ダメージ軽減", "硬くなる", "resistance"],
        "id": {"Java版": "resistance", "統合版": "resistance"}
    },
    "fire_resistance": {
        "name": "火炎耐性",
        "desc": "火に関するダメージを無効化する。",
        "category": "エフェクト",
        "aliases": ["火炎耐性", "火耐性", "燃えない", "マグマ平気", "fire_resistance"],
        "id": {"Java版": "fire_resistance", "統合版": "fire_resistance"}
    },
    "water_breathing": {
        "name": "水中呼吸",
        "desc": "酸素バーが減少しなくなる。",
        "category": "エフェクト",
        "aliases": ["水中呼吸", "水の中", "溺れない", "water_breathing"],
        "id": {"Java版": "water_breathing", "統合版": "water_breathing"}
    },
    "invisibility": {
        "name": "透明化",
        "desc": "透明になる。",
        "category": "エフェクト",
        "aliases": ["透明化", "透明", "消える", "姿を消す", "invisibility"],
        "id": {"Java版": "invisibility", "統合版": "invisibility"}
    },
    "blindness": {
        "name": "盲目",
        "desc": "視界が黒い霧によって狭まり、ダッシュやクリティカル攻撃ができなくなる。",
        "category": "エフェクト",
        "aliases": ["盲目", "目が見えない", "暗闇", "blindness"],
        "id": {"Java版": "blindness", "統合版": "blindness"}
    },
    "night_vision": {
        "name": "暗視",
        "desc": "暗闇でも視界が明るくなる。",
        "category": "エフェクト",
        "aliases": ["暗視", "暗いところが見える", "夜見える", "night_vision"],
        "id": {"Java版": "night_vision", "統合版": "night_vision"}
    },
    "hunger": {
        "name": "空腹",
        "desc": "満腹度を速く減少させる。",
        "category": "エフェクト",
        "aliases": ["空腹", "お腹が空く", "腹減り", "hunger"],
        "id": {"Java版": "hunger", "統合版": "hunger"}
    },
    "weakness": {
        "name": "弱体化",
        "desc": "近接攻撃の攻撃力が低下する。",
        "category": "エフェクト",
        "aliases": ["弱体化", "弱くなる", "弱体", "weakness"],
        "id": {"Java版": "weakness", "統合版": "weakness"}
    },
    "poison": {
        "name": "毒",
        "desc": "時間経過とともに体力が減少する（体力が１になると減少しなくなる）。",
        "category": "エフェクト",
        "aliases": ["毒", "どく", "poison"],
        "id": {"Java版": "poison", "統合版": "poison"}
    },
    "fatal_poison": {
        "name": "致死毒",
        "desc": "時間経過とともに体力が減少し死に至る（統合版限定）。",
        "category": "エフェクト",
        "aliases": ["致死毒", "死ぬ毒", "fatal_poison"],
        "id": {"Java版": None, "統合版": "fatal_poison"}
    },
    "wither": {
        "name": "衰弱",
        "desc": "時間経過とともに体力が減少し死に至る。体力バーが黒くなる。",
        "category": "エフェクト",
        "aliases": ["衰弱", "ウィザー", "wither"],
        "id": {"Java版": "wither", "統合版": "wither"}
    },
    "health_boost": {
        "name": "体力増強",
        "desc": "体力の最大値が増加する。",
        "category": "エフェクト",
        "aliases": ["体力増強", "HPアップ", "体力を増やす", "health_boost"],
        "id": {"Java版": "health_boost", "統合版": "health_boost"}
    },
    "absorption": {
        "name": "衝撃吸収",
        "desc": "一時的に体力が増加する（黄色のハート）。",
        "category": "エフェクト",
        "aliases": ["衝撃吸収", "バリア", "黄色いハート", "absorption"],
        "id": {"Java版": "absorption", "統合版": "absorption"}
    },
    "saturation": {
        "name": "満腹度回復",
        "desc": "満腹度と隠し満腹度が上昇する。",
        "category": "エフェクト",
        "aliases": ["満腹度回復", "お腹いっぱい", "満腹", "saturation"],
        "id": {"Java版": "saturation", "統合版": "saturation"}
    },
    "glowing": {
        "name": "発光",
        "desc": "エンティティが縁取られ、ブロック越しでも視認できるようになる（Java版限定）。",
        "category": "エフェクト",
        "aliases": ["発光", "光る", "縁取り", "glowing"],
        "id": {"Java版": "glowing", "統合版": None}
    },
    "levitation": {
        "name": "浮遊",
        "desc": "エンティティが空中に浮き上がる。",
        "category": "エフェクト",
        "aliases": ["浮遊", "浮く", "ふわふわ", "levitation"],
        "id": {"Java版": "levitation", "統合版": "levitation"}
    },
    "slow_falling": {
        "name": "低速落下",
        "desc": "落下速度が低下し、落下ダメージを受けなくなる。",
        "category": "エフェクト",
        "aliases": ["低速落下", "ゆっくり落ちる", "落下耐性", "slow_falling"],
        "id": {"Java版": "slow_falling", "統合版": "slow_falling"}
    },
    "conduit_power": {
        "name": "コンジットのパワー",
        "desc": "水中での採掘速度上昇、視界改善、酸素減少停止。",
        "category": "エフェクト",
        "aliases": ["コンジットのパワー", "コンジット", "海王", "conduit_power"],
        "id": {"Java版": "conduit_power", "統合版": "conduit_power"}
    },
    "dolphins_grace": {
        "name": "イルカの加護",
        "desc": "水中での移動速度が上昇する（Java版限定）。",
        "category": "エフェクト",
        "aliases": ["イルカの加護", "イルカ", "水中ダッシュ", "dolphins_grace"],
        "id": {"Java版": "dolphins_grace", "統合版": None}
    },
    "bad_omen": {
        "name": "不吉な予感",
        "desc": "村に入ると襲撃イベントが発生する。",
        "category": "エフェクト",
        "aliases": ["不吉な予感", "襲撃", "旗持ち", "bad_omen"],
        "id": {"Java版": "bad_omen", "統合版": "bad_omen"}
    },
    "hero_of_the_village": {
        "name": "村の英雄",
        "desc": "村人との取引が割引され、贈り物をもらえることがある。",
        "category": "エフェクト",
        "aliases": ["村の英雄", "英雄", "割引", "hero_of_the_village"],
        "id": {"Java版": "hero_of_the_village", "統合版": "hero_of_the_village"}
    },
    "darkness": {
        "name": "暗黒",
        "desc": "周囲が定期的に暗くなる。ウォーデンなどが付与する。",
        "category": "エフェクト",
        "aliases": ["暗黒", "暗闇", "ウォーデン", "darkness"],
        "id": {"Java版": "darkness", "統合版": "darkness"}
    }
}