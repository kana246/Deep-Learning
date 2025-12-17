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
    }
}
def template_requires_item(template: str) -> bool:
    return "{item_id}" in template
