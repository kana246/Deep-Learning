#command_data.py

commands = {
    "give": {
        "name": "付与",
        "desc": "{item}をプレイヤーに与える",
        "aliases": [
          "ほしい", "欲しい", "ちょうだい", "ください", "くれ", "くれる", 
          "くれよ", "くれませんか", "ちょーだい","もらう", "貰う",
          "もらえますか", "もらって", "取得", "手に入れる", "手に入れたい", 
          "手に入る", "ゲット","与える", "あげる", "あたえる", "プレゼント", 
          "give", "渡す", "アイテムちょうだい", "アイテムを出す",
          "アイテムをくれる", "出す", "出して", "出してほしい", 
          "アイテムが欲しい", "入手", "支給", "取り出す",
          "ドロップ", "コマンドで出す", "アイテム取得", "アイテム追加", 
          "アイテムを追加", "アイテムがほしい"
        ],
        "template": {
            "統合版": "/give {target} {item_id}",
            "Java版": "/give {target} {item_id}"
        },
        "note": "アイテムIDは後で選べます"
    },
    "effect": {
        "name": "効果付与",
        "desc": "プレイヤーに効果を与える",
        "aliases": ["飛ぶ"],
        "template": {
            "統合版": [
                "/effect {target} {effect_id}",
                "/effect {target} {effect_id}"
            ],
            "Java版": [
                "/effect give {target} {effect_id}",
                "/effect give {target} {effect_id}"
            ]
        },
        "note": "効果IDや強さ、秒数は変更可能です"
    },
    "summon": {
        "name": "召喚",
        "desc": "{mob}を召喚する",
        "aliases": [
            "召喚", "しょうかん", "呼ぶ", "よぶ", "出す", "だす",
            "スポーン", "spawn", "summon", "出現", "出現させる",
            "呼び出す", "呼び出し", "生成", "せいせい"
        ],
        "template": {
            "統合版": "/summon {mob_id}",
            "Java版": "/summon {mob_id}"
        },
        "note": "座標を指定する場合は ~ ~ ~ を追加できます"
    },
    "weather_clear": {
        "name": "天気を晴れに",
        "desc": "天気を晴れにする",
        "aliases": [
            "晴れ", "はれ", "晴れに", "晴れにして", "天気晴れ",
            "快晴", "かいせい", "clear", "sunny"
        ],
        "template": {
            "統合版": "/weather clear",
            "Java版": "/weather clear"
        },
        "note": ""
    },
    "weather_rain": {
        "name": "天気を雨に",
        "desc": "天気を雨にする",
        "aliases": [
            "雨", "あめ", "雨に", "雨にして", "天気雨",
            "rain", "降らせる"
        ],
        "template": {
            "統合版": "/weather rain",
            "Java版": "/weather rain"
        },
        "note": ""
    },
    "weather_thunder": {
        "name": "天気を雷雨に",
        "desc": "天気を雷雨にする",
        "aliases": [
            "雷", "かみなり", "雷雨", "らいう", "雷にして",
            "thunder", "storm", "サンダー"
        ],
        "template": {
            "統合版": "/weather thunder",
            "Java版": "/weather thunder"
        },
        "note": ""
    },
    "time_day": {
        "name": "時間を昼に",
        "desc": "時間を昼にする",
        "aliases": [
            "昼", "ひる", "昼に", "昼にして", "朝", "あさ",
            "day", "morning", "デイ"
        ],
        "template": {
            "統合版": "/time set day",
            "Java版": "/time set day"
        },
        "note": ""
    },
    "time_night": {
        "name": "時間を夜に",
        "desc": "時間を夜にする",
        "aliases": [
            "夜", "よる", "夜に", "夜にして", "night", "ナイト"
        ],
        "template": {
            "統合版": "/time set night",
            "Java版": "/time set night"
        },
        "note": ""
    },
    "time_midnight": {
        "name": "時間を深夜に",
        "desc": "時間を深夜にする",
        "aliases": [
            "深夜", "しんや", "真夜中", "まよなか", "midnight"
        ],
        "template": {
            "統合版": "/time set midnight",
            "Java版": "/time set midnight"
        },
        "note": ""
    },
    "time_noon": {
        "name": "時間を正午に",
        "desc": "時間を正午にする",
        "aliases": [
            "正午", "しょうご", "真昼", "まひる", "noon"
        ],
        "template": {
            "統合版": "/time set noon",
            "Java版": "/time set noon"
        },
        "note": ""
    },
    "gamemode_survival": {
        "name": "サバイバルモード",
        "desc": "ゲームモードをサバイバルに変更",
        "aliases": [
            "サバイバル", "さばいばる", "survival", "サバイバルモード",
            "生存", "せいぞん"
        ],
        "template": {
            "統合版": "/gamemode survival",
            "Java版": "/gamemode survival"
        },
        "note": ""
    },
    "gamemode_creative": {
        "name": "クリエイティブモード",
        "desc": "ゲームモードをクリエイティブに変更",
        "aliases": [
            "クリエイティブ", "くりえいてぃぶ", "creative", "クリエイティブモード",
            "クリエ", "建築", "けんちく"
        ],
        "template": {
            "統合版": "/gamemode creative",
            "Java版": "/gamemode creative"
        },
        "note": ""
    },
    "gamemode_adventure": {
        "name": "アドベンチャーモード",
        "desc": "ゲームモードをアドベンチャーに変更",
        "aliases": [
            "アドベンチャー", "あどべんちゃー", "adventure", "アドベンチャーモード"
        ],
        "template": {
            "統合版": "/gamemode adventure",
            "Java版": "/gamemode adventure"
        },
        "note": ""
    },
    "gamemode_spectator": {
        "name": "スペクテイターモード",
        "desc": "ゲームモードをスペクテイターに変更",
        "aliases": [
            "スペクテイター", "すぺくていたー", "spectator", "スペクテイターモード",
            "観戦", "かんせん", "観察"
        ],
        "template": {
            "統合版": "/gamemode spectator",
            "Java版": "/gamemode spectator"
        },
        "note": "統合版では利用できない場合があります"
    },
    "difficulty_peaceful": {
        "name": "難易度をピースフルに",
        "desc": "難易度をピースフルに変更",
        "aliases": [
            "ピースフル", "ぴーすふる", "peaceful", "平和", "へいわ",
            "簡単", "かんたん"
        ],
        "template": {
            "統合版": "/difficulty peaceful",
            "Java版": "/difficulty peaceful"
        },
        "note": ""
    },
    "difficulty_easy": {
        "name": "難易度をイージーに",
        "desc": "難易度をイージーに変更",
        "aliases": [
            "イージー", "いーじー", "easy"
        ],
        "template": {
            "統合版": "/difficulty easy",
            "Java版": "/difficulty easy"
        },
        "note": ""
    },
    "difficulty_normal": {
        "name": "難易度をノーマルに",
        "desc": "難易度をノーマルに変更",
        "aliases": [
            "ノーマル", "のーまる", "normal", "普通", "ふつう"
        ],
        "template": {
            "統合版": "/difficulty normal",
            "Java版": "/difficulty normal"
        },
        "note": ""
    },
    "difficulty_hard": {
        "name": "難易度をハードに",
        "desc": "難易度をハードに変更",
        "aliases": [
            "ハード", "はーど", "hard", "難しい", "むずかしい"
        ],
        "template": {
            "統合版": "/difficulty hard",
            "Java版": "/difficulty hard"
        },
        "note": ""
    },
    "teleport": {
        "name": "テレポート",
        "desc": "指定した座標にテレポートする",
        "aliases": [
            "テレポート", "てれぽーと", "tp", "teleport", "ワープ",
            "わーぷ", "移動", "いどう", "瞬間移動"
        ],
        "template": {
            "統合版": "/tp {target} ~ ~ ~",
            "Java版": "/tp {target} ~ ~ ~"
        },
        "note": "座標を指定する場合は ~ を数値に変更してください"
    },
    "kill": {
        "name": "キル",
        "desc": "対象を倒す",
        "aliases": [
            "キル", "きる", "kill", "倒す", "たおす", "殺す",
            "死ぬ", "しぬ", "death"
        ],
        "template": {
            "統合版": "/kill {target}",
            "Java版": "/kill {target}"
        },
        "note": ""
    },
    "clear": {
        "name": "インベントリクリア",
        "desc": "インベントリをクリアする",
        "aliases": [
            "クリア", "くりあ", "clear", "消す", "けす",
            "削除", "さくじょ", "インベントリ削除", "持ち物削除"
        ],
        "template": {
            "統合版": "/clear {target}",
            "Java版": "/clear {target}"
        },
        "note": ""
    },
    "setworldspawn": {
        "name": "ワールドスポーン設定",
        "desc": "ワールドのスポーン地点を設定",
        "aliases": [
            "スポーン地点", "すぽーんちてん", "setworldspawn", "リスポーン",
            "スポーン設定"
        ],
        "template": {
            "統合版": "/setworldspawn",
            "Java版": "/setworldspawn"
        },
        "note": ""
    },
    "spawnpoint": {
        "name": "個人スポーン設定",
        "desc": "プレイヤーのスポーン地点を設定",
        "aliases": [
            "個人スポーン", "spawnpoint", "リスポーン地点"
        ],
        "template": {
            "統合版": "/spawnpoint {target}",
            "Java版": "/spawnpoint {target}"
        },
        "note": ""
    },
    "xp_add": {
        "name": "経験値付与",
        "desc": "経験値を付与する",
        "aliases": [
            "経験値", "けいけんち", "xp", "経験値ちょうだい",
            "レベル", "れべる", "level"
        ],
        "template": {
            "統合版": "/xp 100 {target}",
            "Java版": "/experience add {target} 100"
        },
        "note": "数値を変更して経験値量を調整できます"
    },
    "locate": {
        "name": "構造物の位置を探す",
        "desc": "{structure}の座標を探す",
        "aliases": [
            "locate", "探す", "さがす", "検索", "けんさく", "位置",
            "いち", "座標", "ざひょう", "場所", "ばしょ", "どこ"
        ],
        "template": {
            "統合版": "/locate structure {structure_id}",
            "Java版": "/locate structure {structure_id}"
        },
        "note": "最も近い構造物の座標を表示します"
    }
}
def template_requires_item(template: str) -> bool:
    return "{item_id}" in template
