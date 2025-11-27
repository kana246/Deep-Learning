#ui.py
import gradio as gr

# --- 複合マッチ対応コマンド候補生成関数 ---
def generate_command_candidates(user_input, edition, items, commands):
    user_input = user_input.lower().strip()
    matched_items = [
        item for item in items.values()
        if any(alias in user_input for alias in item.get("aliases", []))
    ]

    results = []
    for cmd_key, cmd in commands.items():
        if any(alias in user_input for alias in cmd.get("aliases", [])):
            templates = cmd["template"].get(edition)
            if isinstance(templates, str):
                if "{item_id}" in templates and matched_items:
                    for item in matched_items:
                        filled = templates.replace("{item_id}", item["id"][edition])
                        results.append({
                            "cmd_template": templates,
                            "desc": cmd["desc"],  # ← {item} を残す
                            "note": cmd.get("note", ""),
                            "cmd": filled,
                            "item_name": item["name"]  # ← アイテム名を別フィールドで渡す
                        })

                else:
                    results.append({
                        "cmd_template": templates,
                        "desc": cmd["desc"],
                        "note": cmd.get("note", ""),
                        "cmd": templates
                    })
            elif isinstance(templates, list):
                for t in templates:
                    results.append({
                        "cmd_template": t,
                        "desc": cmd["desc"],
                        "note": cmd.get("note", ""),
                        "cmd": t
                    })

    return results

# --- アイテム図鑑 UI クラス ---
class ItemDictionaryUI:
    def __init__(self, items, search_func):
        self.items = items
        self.search_func = search_func
        self.back_button = None

    def render(self):
        with gr.Column(visible=False) as container:
            gr.Markdown("### 📘 アイテムID図鑑")

            with gr.Row():
                self.query = gr.Textbox(label="🔍 キーワード", scale=2)
                self.category = gr.Dropdown(
                    choices=["すべて"] + sorted({item.get("category", "なし") for item in self.items.values()}),
                    value="すべて",
                    label="カテゴリ",
                    scale=1
                )

            with gr.Column(elem_id="item-result-box"):
                self.result_markdown = gr.Markdown("ここに検索結果が表示されます", elem_id="item-result")
                
            self.back_button = gr.Button("🔙 ホームに戻る", elem_id="fixed-back")
            self.query.change(fn=self._update_results, inputs=[self.query, self.category], outputs=self.result_markdown)
            self.category.change(fn=self._update_results, inputs=[self.query, self.category], outputs=self.result_markdown)

            # 初期状態：すべて表示（空キーワード & カテゴリなし）をセット
            self.result_markdown.value = self._update_results("", "すべて")

        return container

    def _update_results(self, keyword, category):
        if category == "すべて":
            category = None
        results = self.search_func(keyword, category)
        if not results:
            return "⚠️ 該当するアイテムが見つかりませんでした。"

        lines = []
        for item_id, item in results:
            line = f"**{item['name']}** (`{item_id}`)\n- 📦 {item['desc']}\n- 🏷️ カテゴリ: {item.get('category', 'なし')}"
            lines.append(line)
        return "\n\n---\n\n".join(lines)

# --- コマンド図鑑 UI クラス ---
class CommandDictionaryUI:
    def __init__(self, commands, search_func):
        self.commands = commands
        self.search_func = search_func
        self.back_button = None

    def render(self):
        with gr.Column(visible=False) as container:
            gr.Markdown("### 🧾 コマンド図鑑")

            with gr.Row():
                self.query = gr.Textbox(label="🔍 キーワード", scale=2)

            with gr.Column(elem_id="item-result-box"):
                self.result_markdown = gr.Markdown("ここに検索結果が表示されます", elem_id="item-result")

            self.back_button = gr.Button("🔙 ホームに戻る", elem_id="fixed-back")

            self.query.change(fn=self._update_results, inputs=[self.query], outputs=[self.result_markdown])

            # 初期状態：全コマンドを表示
            self.result_markdown.value = self._update_results("")

        return container

    def _update_results(self, keyword):
        results = self.search_func(keyword)
        if not results:
            return "⚠️ 該当するコマンドが見つかりませんでした。"

        lines = []
        for cmd_key, cmd in results:
            template = cmd["template"]
            template_str = ""
            if isinstance(template.get("統合版"), list):
                template_str = "\n".join(f"`{t}`" for t in template["統合版"])
            else:
                template_str = f"`{template['統合版']}`"

            line = f"### 🛠️ {cmd['name']}\n{template_str}\n- 📘 説明: {cmd['desc']}"
            lines.append(line)

        return "\n\n---\n\n".join(lines)
