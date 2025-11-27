import streamlit as st

# ページ設定（最初に配置）
st.set_page_config(
    page_title="マインクラフトコマンド生成ツール",
    page_icon="🎮",
    layout="centered",
)

# データのインポート（エラーハンドリング付き）
try:
    from item_data import items
except ImportError:
    st.error("❌ item_data.py が見つかりません")
    st.stop()

try:
    from command_data import commands
except ImportError:
    st.error("❌ command_data.py が見つかりません")
    st.stop()

# 検索関数の定義（logic.pyが無い場合のフォールバック）
def search_items(query, category=None):
    """アイテムを検索"""
    query = query.lower().strip()
    results = []
    
    for item_id, item in items.items():
        if category and category != "すべて" and item.get("category") != category:
            continue
        if query in item_id.lower():
            results.append((item_id, item))
        elif query in item["name"].lower():
            results.append((item_id, item))
        elif query in item["desc"].lower():
            results.append((item_id, item))
        elif any(query in alias.lower() for alias in item.get("aliases", [])):
            results.append((item_id, item))
    
    return results

def search_commands(query):
    """コマンドを検索"""
    query = query.lower().strip()
    results = []
    
    for cmd_key, cmd in commands.items():
        if query in cmd_key.lower():
            results.append((cmd_key, cmd))
        elif query in cmd["name"].lower():
            results.append((cmd_key, cmd))
        elif query in cmd["desc"].lower():
            results.append((cmd_key, cmd))
        elif any(query in alias.lower() for alias in cmd.get("aliases", [])):
            results.append((cmd_key, cmd))
    
    return results

def generate_command_candidates(text, edition, items_dict, commands_dict):
    """自然言語からコマンド候補を生成"""
    candidates = []
    text_lower = text.lower()
    
    for cmd_key, cmd in commands_dict.items():
        if (cmd_key.lower() in text_lower or 
            any(alias.lower() in text_lower for alias in cmd.get("aliases", []))):
            
            template = cmd["template"]
            
            if isinstance(template, dict):
                cmd_template = template.get(edition, "")
            else:
                cmd_template = template
            
            if isinstance(cmd_template, list):
                cmd_template = cmd_template[0] if cmd_template else ""
            
            if "{item_id}" in str(cmd_template):
                for item_id, item in items_dict.items():
                    if (item["name"].lower() in text_lower or
                        any(alias.lower() in text_lower for alias in item.get("aliases", []))):
                        
                        item_edition_id = item["id"].get(edition, "")
                        if item_edition_id:
                            final_cmd = cmd_template.replace("{item_id}", item_edition_id)
                            candidates.append({
                                "cmd": final_cmd,
                                "desc": cmd["desc"],
                                "note": cmd["note"],
                                "cmd_template": cmd_template,
                                "item_name": item["name"]
                            })
            else:
                candidates.append({
                    "cmd": cmd_template,
                    "desc": cmd["desc"],
                    "note": cmd["note"],
                    "cmd_template": cmd_template
                })
    
    return candidates

# カスタムCSS
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #e8f5e9 !important;
}

.main {
    max-width: 1400px !important;
}

h1 a, h2 a, h3 a, h4 a {
    display: none !important;
}

* {
    animation-duration: 0s !important;
    transition-duration: 0s !important;
}
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if 'edition' not in st.session_state:
    st.session_state.edition = '統合版'

# タイトル
st.title("🎮 マインクラフトコマンド生成ツール")
st.markdown("---")

# サイドバーメニュー
st.sidebar.markdown("### 🎯 メニュー")
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "📘 アイテム図鑑", "🧾 コマンド図鑑", "⚙️ 設定"],
    label_visibility="collapsed"
)

# 設定
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ バージョン設定")
edition = st.sidebar.selectbox(
    "Minecraft エディション",
    ["統合版", "Java版"],
    index=0 if st.session_state.edition == "統合版" else 1
)
st.session_state.edition = edition

# ホームページ
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### 📊 統計情報")
        st.metric("登録アイテム数", f"{len(items)}個")
        st.metric("登録コマンド数", f"{len(commands)}個")
        st.metric("現在のエディション", st.session_state.edition)
    
    with col2:
        st.success("### 📖 使い方")
        st.markdown("""
        1. **コマンド生成**: やりたいことを日本語で入力
        2. **アイテム図鑑**: アイテムを検索・参照
        3. **コマンド図鑑**: コマンドを検索・参照
        4. **設定**: バージョンを変更
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 🚀 主な機能
    
    - 🛠 **コマンド生成**: 自然言語からMinecraftコマンドを生成
    - 📘 **アイテム図鑑**: 全アイテムの検索とID確認
    - 🧾 **コマンド図鑑**: コマンド一覧と解説
    - ⚙️ **バージョン対応**: 統合版・Java版の両方に対応
    """)

# コマンド生成ページ
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    st.markdown("### やりたいことを入力してください")
    user_input = st.text_input(
        "日本語で入力",
        placeholder="例: ダイヤモンドが欲しい、オークの木をちょうだい"
    )
    
    if user_input:
        candidates = generate_command_candidates(
            user_input, 
            st.session_state.edition, 
            items, 
            commands
        )
        
        if candidates:
            st.success(f"✅ {len(candidates)}個のコマンド候補が見つかりました")
            
            labels = []
            for c in candidates:
                if "{item}" in c["desc"] and "item_name" in c:
                    desc = c["desc"].replace("{item}", c["item_name"])
                else:
                    desc = c["desc"]
                labels.append(f"{c['cmd']} ({desc})")
            
            selected_label = st.selectbox("コマンド候補を選択", options=labels)
            
            if selected_label:
                index = labels.index(selected_label)
                selected = candidates[index]
                
                st.markdown("---")
                st.markdown("### ✅ コマンド詳細")
                st.code(selected["cmd"], language="bash")
                
                col1, col2 = st.columns(2)
                with col1:
                    desc = selected['desc']
                    if "{item}" in desc and "item_name" in selected:
                        desc = desc.replace("{item}", selected["item_name"])
                    st.info(f"**解説**: {desc}")
                with col2:
                    st.info(f"**補足**: {selected['note']}")
                
                template = selected["cmd_template"]
                item_visible = "{item_id}" in str(template)
                
                if item_visible:
                    st.markdown("---")
                    st.markdown("### 🎯 アイテムを変更")
                    
                    item_names = [item["name"] for item in items.values()]
                    selected_item_name = st.selectbox("別のアイテムを選択", options=item_names)
                    
                    for item in items.values():
                        if item["name"] == selected_item_name:
                            item_id = item["id"].get(st.session_state.edition)
                            if item_id:
                                new_cmd = template.replace("{item_id}", item_id)
                                st.code(new_cmd, language="bash")
                                new_desc = selected["desc"].replace("{item}", item["name"])
                                st.info(f"**更新後の解説**: {new_desc}")
                                break
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.info("""
            **ヒント**: 以下のようなキーワードで試してみてください
            - 「ダイヤモンドが欲しい」
            - 「オークの木をちょうだい」
            - 「アイテムをください」
            """)

# アイテム図鑑ページ
elif menu == "📘 アイテム図鑑":
    st.header("📘 アイテム図鑑")
    
    categories = list(set([item.get("category", "その他") for item in items.values()]))
    category_filter = st.selectbox(
        "カテゴリで絞り込み",
        options=["すべて"] + sorted(categories)
    )
    
    search_query = st.text_input(
        "🔍 アイテム名で検索",
        placeholder="例: オーク、ダイヤモンド"
    )
    
    if search_query:
        results = search_items(search_query, None if category_filter == "すべて" else category_filter)
        
        if results:
            st.success(f"✅ {len(results)}個のアイテムが見つかりました")
            
            for item_id, item in results[:20]:
                with st.expander(f"📦 {item['name']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**説明**: {item['desc']}")
                        st.write(f"**カテゴリ**: {item.get('category', 'その他')}")
                        st.write(f"**スタックサイズ**: {item.get('stack_size', 64)}")
                    
                    with col2:
                        st.write(f"**統合版ID**: `{item['id'].get('統合版', 'なし')}`")
                        st.write(f"**Java版ID**: `{item['id'].get('Java版', 'なし')}`")
                    
                    if item.get("aliases"):
                        st.write(f"**別名**: {', '.join(item['aliases'][:5])}")
        else:
            st.warning("⚠️ 該当するアイテムが見つかりませんでした")
    else:
        st.info("👆 上の検索ボックスにキーワードを入力してください")
        st.markdown(f"**登録アイテム総数**: {len(items)}個")

# コマンド図鑑ページ
elif menu == "🧾 コマンド図鑑":
    st.header("🧾 コマンド図鑑")
    
    search_query = st.text_input(
        "🔍 コマンドで検索",
        placeholder="例: give、付与、アイテム"
    )
    
    if search_query:
        results = search_commands(search_query)
        
        if results:
            st.success(f"✅ {len(results)}個のコマンドが見つかりました")
            
            for cmd_key, cmd in results:
                with st.expander(f"🎮 {cmd['name']} ({cmd_key})"):
                    st.write(f"**説明**: {cmd['desc']}")
                    st.write(f"**補足**: {cmd['note']}")
                    
                    template = cmd['template']
                    if isinstance(template, dict):
                        for edition_name, tmpl in template.items():
                            st.write(f"**{edition_name}**:")
                            if isinstance(tmpl, list):
                                st.code(tmpl[0], language="bash")
                            else:
                                st.code(tmpl, language="bash")
                    else:
                        st.code(str(template), language="bash")
                    
                    if cmd.get("aliases"):
                        st.write(f"**別名**: {', '.join(cmd['aliases'][:10])}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
    else:
        st.info("👆 上の検索ボックスにキーワードを入力してください")
        
        st.markdown("---")
        st.markdown("### 📋 全コマンド一覧")
        
        for cmd_key, cmd in commands.items():
            with st.expander(f"🎮 {cmd['name']}"):
                st.write(f"**説明**: {cmd['desc']}")
                st.write(f"**補足**: {cmd['note']}")
                
                template = cmd['template']
                if isinstance(template, dict):
                    for edition_name, tmpl in template.items():
                        st.write(f"**{edition_name}**:")
                        if isinstance(tmpl, list):
                            st.code(tmpl[0], language="bash")
                        else:
                            st.code(tmpl, language="bash")

# 設定ページ
elif menu == "⚙️ 設定":
    st.header("⚙️ 設定メニュー")
    
    st.markdown("### 🎮 バージョン設定")
    st.info(f"現在のエディション: **{st.session_state.edition}**")
    st.markdown("エディションはサイドバーから変更できます")
    
    st.markdown("---")
    st.markdown("### 📊 システム情報")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("登録アイテム数", f"{len(items)}個")
    with col2:
        st.metric("登録コマンド数", f"{len(commands)}個")
    with col3:
        st.metric("対応エディション", "2種類")
    
    st.markdown("---")
    st.markdown("### 📝 クレジット")
    st.markdown("""
    **Minecraft コマンド生成ツール**
    
    - Gradio版からStreamlit版に移植
    - 統合版・Java版の両方に対応
    - 自然言語からコマンドを生成
    
    *Powered by Streamlit*
    """)

st.markdown("---")
st.markdown("*Minecraft コマンド生成ツール - Powered by Streamlit*")
