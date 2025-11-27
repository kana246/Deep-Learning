import streamlit as st
import base64
from pathlib import Path

# ページ設定
st.set_page_config(
    page_title="Minecraftコマンド生成ツール",
    page_icon="⛏️",
    layout="centered",
)

# CSSスタイル
st.markdown("""
<style>
/* ====== サイドバー固定 ====== */
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

[data-testid="stSidebar"] * {
    cursor: default !important;
}

[data-testid="stSidebar"] button,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] input[type="radio"] {
    cursor: pointer !important;
}

/* ====== メインエリア ====== */
.main {
    margin-left: 280px !important;
}

.block-container {
    max-width: 1200px !important;
    padding-top: 2rem !important;
}

/* ====== 見出しのアンカーリンク非表示 ====== */
h1::before, h2::before, h3::before, h4::before {
    content: none !important;
    display: none !important;
}

h1 a, h2 a, h3 a, h4 a {
    display: none !important;
    pointer-events: none !important;
}

[data-testid="stHeaderActionElements"] {
    display: none !important;
}

/* ====== アニメーション無効化 ====== */
* {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
}

/* ====== ボタンスタイル ====== */
.stButton button {
    width: 100%;
    border-radius: 8px;
    font-weight: 500;
}

/* ====== スマホ対応 ====== */
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
if 'selected_command' not in st.session_state:
    st.session_state.selected_command = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ''

# サンプルデータ（item_data.py と command_data.py の代わり）
ITEMS = {
    'diamond': {'name': 'ダイヤモンド', 'id': {'統合版': 'diamond', 'Java版': 'minecraft:diamond'}},
    'iron_ingot': {'name': '鉄インゴット', 'id': {'統合版': 'iron_ingot', 'Java版': 'minecraft:iron_ingot'}},
    'gold_ingot': {'name': '金インゴット', 'id': {'統合版': 'gold_ingot', 'Java版': 'minecraft:gold_ingot'}},
}

COMMANDS = [
    {
        'keywords': ['アイテム', '与える', 'あげる'],
        'cmd_template': '/give @s {item_id} 1',
        'desc': '{item}を1個与える',
        'note': '@sは自分自身を指定'
    },
    {
        'keywords': ['テレポート', 'TP', '移動'],
        'cmd_template': '/tp @s ~ ~10 ~',
        'desc': '自分を10ブロック上に移動',
        'note': '~は相対座標'
    },
    {
        'keywords': ['天気', '晴れ', '快晴'],
        'cmd_template': '/weather clear',
        'desc': '天気を晴れにする',
        'note': '雨や雷を止めます'
    },
]

def search_commands(query, edition):
    """コマンドを検索"""
    results = []
    query_lower = query.lower()
    
    for cmd in COMMANDS:
        if any(keyword in query_lower for keyword in cmd['keywords']):
            cmd_copy = cmd.copy()
            if '{item_id}' in cmd_copy['cmd_template']:
                # デフォルトアイテムを設定
                default_item = list(ITEMS.values())[0]
                cmd_copy['cmd'] = cmd_copy['cmd_template'].replace('{item_id}', default_item['id'][edition])
                cmd_copy['item_name'] = default_item['name']
            else:
                cmd_copy['cmd'] = cmd_copy['cmd_template']
            results.append(cmd_copy)
    
    return results

# タイトル
st.title("⛏️ Minecraftコマンド生成ツール")
st.markdown("---")

# サイドバーメニュー
st.sidebar.markdown("### 🎮 メニュー")
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ホーム", "🛠 コマンド生成", "📘 アイテム図鑑", "🧾 コマンド図鑑", "⚙️ 設定"],
    key="main_menu",
    label_visibility="collapsed"
)

# ホーム画面
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📚 主な機能")
        st.markdown("""
        - 🛠 **コマンド生成**: 日本語でやりたいことを入力
        - 📘 **アイテム図鑑**: アイテム一覧と検索
        - 🧾 **コマンド図鑑**: よく使うコマンド集
        - ⚙️ **設定**: バージョン選択など
        """)
    
    with col2:
        st.markdown("### 🎯 使い方")
        st.markdown("""
        1. 左メニューから機能を選択
        2. やりたいことを日本語で入力
        3. コマンドが自動生成されます
        4. コピー＆ペーストして使用
        """)
    
    st.markdown("---")
    st.info("💡 左のサイドバーから機能を選択してください")

# コマンド生成画面
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    st.markdown("### やりたいことを入力してください")
    user_input = st.text_input(
        "日本語で入力（例: ダイヤモンドを与える、テレポート、天気を晴れに）",
        value=st.session_state.user_input,
        key="command_input"
    )
    
    if user_input:
        st.session_state.user_input = user_input
        candidates = search_commands(user_input, st.session_state.edition)
        
        if candidates:
            st.success(f"✅ {len(candidates)}件のコマンドが見つかりました")
            
            for i, cmd in enumerate(candidates):
                with st.expander(f"📋 {cmd['desc']}", expanded=(i==0)):
                    st.code(cmd['cmd'], language='bash')
                    
                    # アイテム選択（必要な場合のみ）
                    if '{item_id}' in cmd['cmd_template']:
                        st.markdown("**アイテムを変更:**")
                        selected_item = st.selectbox(
                            "アイテム選択",
                            options=[item['name'] for item in ITEMS.values()],
                            key=f"item_select_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # アイテム変更時にコマンドを更新
                        for item in ITEMS.values():
                            if item['name'] == selected_item:
                                updated_cmd = cmd['cmd_template'].replace(
                                    '{item_id}', 
                                    item['id'][st.session_state.edition]
                                )
                                st.code(updated_cmd, language='bash')
                                break
                    
                    st.markdown(f"**解説:** {cmd['desc']}")
                    if 'note' in cmd:
                        st.markdown(f"**補足:** {cmd['note']}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.markdown("**ヒント:** 以下のキーワードを試してください")
            st.markdown("- アイテムを与える")
            st.markdown("- テレポート")
            st.markdown("- 天気を変える")

# アイテム図鑑
elif menu == "📘 アイテム図鑑":
    st.header("📘 アイテム図鑑")
    
    st.markdown("### アイテム一覧")
    
    search_query = st.text_input("🔍 アイテムを検索", placeholder="例: ダイヤ、鉄")
    
    filtered_items = ITEMS
    if search_query:
        filtered_items = {
            k: v for k, v in ITEMS.items() 
            if search_query.lower() in v['name'].lower()
        }
    
    if filtered_items:
        for item_key, item in filtered_items.items():
            with st.expander(f"📦 {item['name']}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**統合版ID:**")
                    st.code(item['id']['統合版'])
                with col2:
                    st.markdown(f"**Java版ID:**")
                    st.code(item['id']['Java版'])
    else:
        st.warning("該当するアイテムが見つかりませんでした")

# コマンド図鑑
elif menu == "🧾 コマンド図鑑":
    st.header("🧾 コマンド図鑑")
    
    st.markdown("### よく使うコマンド一覧")
    
    for i, cmd in enumerate(COMMANDS):
        with st.expander(f"📌 {cmd['desc']}", expanded=False):
            st.code(cmd['cmd_template'], language='bash')
            st.markdown(f"**解説:** {cmd['desc']}")
            if 'note' in cmd:
                st.markdown(f"**補足:** {cmd['note']}")
            st.markdown(f"**検索キーワード:** {', '.join(cmd['keywords'])}")

# 設定画面
elif menu == "⚙️ 設定":
    st.header("⚙️ 設定")
    
    st.markdown("### Minecraftバージョン")
    edition = st.radio(
        "バージョンを選択",
        ["統合版", "Java版"],
        index=0 if st.session_state.edition == "統合版" else 1,
        key="edition_selector"
    )
    st.session_state.edition = edition
    
    st.success(f"✅ 現在のバージョン: **{st.session_state.edition}**")
    
    st.markdown("---")
    st.markdown("### 📚 その他の機能（準備中）")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📖 サイトの使い方"):
            st.info("使い方ページは準備中です")
        if st.button("📈 コマンド履歴"):
            st.info("履歴機能は準備中です")
    
    with col2:
        if st.button("🖼 背景を変更"):
            st.info("背景変更機能は準備中です")
        if st.button("📝 パッチノート"):
            st.info("パッチノートは準備中です")

# フッター
st.markdown("---")
st.markdown("*Minecraftコマンド生成ツール - Powered by Streamlit*")
st.markdown("🎮 統合版・Java版両対応")
