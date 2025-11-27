import streamlit as st
import pandas as pd
from item_data import items
from command_data import commands
from logic import search_items, search_commands
from ui import generate_command_candidates

# ページ設定
st.set_page_config(
    page_title="マインクラフトコマンド生成ツール",
    page_icon="🎮",
    layout="centered",
)

# カスタムCSS
st.markdown("""
<style>
/* サイドバー固定 */
[data-testid="stSidebar"] {
    position: fixed !important;
    top: 0;
    left: 0;
    width: 280px !important;
    height: 100vh !important;
    background-color: #e8f5e9 !important;
    border-right: 1px solid #e0e0e0;
    padding: 0 !important;
    margin: 0 !important;
    z-index: 1000000;
    overflow: hidden;
    border-radius: 0px 30px 30px 0;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 3rem !important;
    margin-top: 0 !important;
}

[data-testid="stSidebarContent"] {
    overflow-y: auto !important;
    height: 100vh !important;
    padding: 0 1rem 1rem 1rem !important;
    margin: 0 !important;
}

/* メインエリア */
.main {
    margin-left: 280px !important;
}

.block-container {
    max-width: 1400px !important;
    padding-top: 2rem !important;
}

/* テーブルの揺れ対策 */
.stDataFrame, .stTable {
    max-width: 100% !important;
}

table {
    table-layout: fixed !important;
    width: 100% !important;
}

/* 見出しのアンカーリンクを非表示 */
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
    display: none !important;
    pointer-events: none !important;
}

/* アニメーション抑制 */
* {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
}

/* スマホ対応 */
@media (max-width: 900px) {
    [data-testid="stSidebar"] {
        position: relative !important;
        width: 100% !important;
        height: auto !important;
        border-right: none !important;
    }
    .main {
        margin-left: 0 !important;
    }
    .block-container {
        max-width: 100% !important;
        padding: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'edition' not in st.session_state:
    st.session_state.edition = '統合版'
if 'user_input' not in st.session_state:
    st.session_state.user_input = ''
if 'selected_command' not in st.session_state:
    st.session_state.selected_command = None
if 'command_candidates' not in st.session_state:
    st.session_state.command_candidates = []

# タイトル
st.title("🎮 マインクラフトコマンド生成ツール")
st.markdown("---")

# サイドバーメニュー
st.sidebar.markdown("### 🎯 メニュー")
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "📘 アイテム図鑑", "🧾 コマンド図鑑", "⚙️ 設定"],
    key="main_menu",
    label_visibility="collapsed"
)

# 設定（サイドバー下部）
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ バージョン設定")
edition = st.sidebar.selectbox(
    "Minecraft エディション",
    ["統合版", "Java版"],
    index=0 if st.session_state.edition == "統合版" else 1,
    key="edition_selector"
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
    
    左のメニューから機能を選択してください！
    """)

# コマンド生成ページ
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    st.markdown("### やりたいことを入力してください")
    user_input = st.text_input(
        "日本語で入力",
        placeholder="例: ダイヤモンドが欲しい、飛びたい",
        key="user_input_box"
    )
    
    if user_input:
        # コマンド候補を生成
        candidates = generate_command_candidates(
            user_input, 
            st.session_state.edition, 
            items, 
            commands
        )
        
        if candidates:
            st.success(f"✅ {len(candidates)}個のコマンド候補が見つかりました")
            
            # 候補をドロップダウンで表示
            labels = []
            for c in candidates:
                if "{item}" in c["desc"] and "item_name" in c:
                    desc = c["desc"].replace("{item}", c["item_name"])
                else:
                    desc = c["desc"]
                labels.append(f"{c['cmd']}({desc})")
            
            selected_label = st.selectbox(
                "コマンド候補を選択",
                options=labels,
                key="command_dropdown"
            )
            
            # 選択されたコマンドの詳細を表示
            if selected_label:
                index = labels.index(selected_label)
                selected = candidates[index]
                
                st.markdown("---")
                st.markdown("### ✅ コマンド詳細")
                
                # コマンド表示
                st.code(selected["cmd"], language="bash")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**解説**: {selected['desc']}")
                with col2:
                    st.info(f"**補足**: {selected['note']}")
                
                # アイテム選択（必要な場合）
                template = selected["cmd_template"]
                item_visible = (
                    (isinstance(template, str) and "{item_id}" in template) or
                    (isinstance(template, list) and any("{item_id}" in t for t in template))
                )
                
                if item_visible:
                    st.markdown("---")
                    st.markdown("### 🎯 アイテムを変更")
                    
                    item_names = [item["name"] for item in items.values()]
                    selected_item_name = st.selectbox(
                        "別のアイテムを選択",
                        options=item_names,
                        key="item_selector"
                    )
                    
                    # 選択されたアイテムでコマンドを更新
                    for item in items.values():
                        if item["name"] == selected_item_name:
                            item_id = item["id"].get(st.session_state.edition)
                            if item_id:
                                if isinstance(template, str):
                                    new_cmd = template.replace("{item_id}", item_id)
                                else:
                                    new_cmd = template[0].replace("{item_id}", item_id)
                                
                                st.code(new_cmd, language="bash")
                                break
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.info("別のキーワードで試してみてください")

# アイテム図鑑ページ
elif menu == "📘 アイテム図鑑":
    st.header("📘 アイテム図鑑")
    
    # カテゴリフィルタ
    categories = list(set([item.get("category", "その他") for item in items.values()]))
    category_filter = st.selectbox(
        "カテゴリで絞り込み",
        options=["すべて"] + sorted(categories),
        key="category_filter"
    )
    
    # 検索ボックス
    search_query = st.text_input(
        "🔍 アイテム名で検索",
        placeholder="例: オーク、ダイヤモンド",
        key="item_search"
    )
    
    # 検索実行
    if search_query:
        results = search_items(search_query, None if category_filter == "すべて" else category_filter)
        
        if results:
            st.success(f"✅ {len(results)}個のアイテムが見つかりました")
            
            # 結果を表示
            for item_id, item in results[:20]:  # 最大20件表示
                with st.expander(f"📦 {item['name']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**説明**: {item['desc']}")
                        st.write(f"**カテゴリ**: {item.get('category', 'その他')}")
                        st.write(f"**スタックサイズ**: {item.get('stack_size', 64)}")
                    
                    with col2:
                        st.write(f"**統合版ID**: `{item['id'].get('統合版', 'なし')}`")
                        st.write(f"**Java版ID**: `{item['id'].get('Java版', 'なし')}`")
                    
                    # エイリアス表示
                    if item.get("aliases"):
                        st.write(f"**別名**: {', '.join(item['aliases'][:5])}")
        else:
            st.warning("⚠️ 該当するアイテムが見つかりませんでした")
    else:
        st.info("👆 上の検索ボックスにキーワードを入力してください")

# コマンド図鑑ページ
elif menu == "🧾 コマンド図鑑":
    st.header("🧾 コマンド図鑑")
    
    # 検索ボックス
    search_query = st.text_input(
        "🔍 コマンドで検索",
        placeholder="例: give、付与、アイテム",
        key="command_search"
    )
    
    if search_query:
        results = search_commands(search_query)
        
        if results:
            st.success(f"✅ {len(results)}個のコマンドが見つかりました")
            
            for cmd_key, cmd in results:
                with st.expander(f"🎮 {cmd['name']} ({cmd_key})"):
                    st.write(f"**説明**: {cmd['desc']}")
                    st.write(f"**補足**: {cmd['note']}")
                    
                    # テンプレート表示
                    template = cmd['template']
                    if isinstance(template, dict):
                        for edition, tmpl in template.items():
                            if isinstance(tmpl, list):
                                st.code(tmpl[0], language="bash")
                            else:
                                st.code(tmpl, language="bash")
                            break
                    
                    # エイリアス表示
                    if cmd.get("aliases"):
                        st.write(f"**別名**: {', '.join(cmd['aliases'][:10])}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
    else:
        st.info("👆 上の検索ボックスにキーワードを入力してください")
        
        # 全コマンド一覧を表示
        st.markdown("---")
        st.markdown("### 📋 全コマンド一覧")
        
        for cmd_key, cmd in commands.items():
            with st.expander(f"🎮 {cmd['name']}"):
                st.write(f"**説明**: {cmd['desc']}")
                st.write(f"**補足**: {cmd['note']}")

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

# フッター
st.markdown("---")
st.markdown("*Minecraft コマンド生成ツール - Powered by Streamlit*")
