import streamlit as st
from pathlib import Path
import sys

# ========== 外部ファイルの読み込み ==========
# デバッグ情報表示
import os

# 現在のディレクトリとファイル一覧を確認
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
files_in_dir = os.listdir(current_dir)

# デバッグ用：起動時にファイル情報を表示
print(f"現在のディレクトリ: {current_dir}")
print(f"ディレクトリ内のファイル: {files_in_dir}")

# データ読み込み
ITEMS = {}
ITEM_CATEGORIES = []
COMMANDS = []
COMMAND_CATEGORIES = []

# item_data.py の読み込み
try:
    # 方法1: 通常のインポート
    from item_data import ITEMS as LOADED_ITEMS
    ITEMS = LOADED_ITEMS
    
    try:
        from item_data import CATEGORIES as ITEM_CATEGORIES
    except (ImportError, AttributeError):
        ITEM_CATEGORIES = list(set([item.get('category', 'その他') for item in ITEMS.values()]))
        ITEM_CATEGORIES.sort()
    
    print(f"✅ item_data.py 読み込み成功: {len(ITEMS)}個")
    
except ImportError as e:
    print(f"❌ item_data.py インポートエラー: {e}")
    
    # 方法2: sys.pathを使った読み込み
    try:
        sys.path.insert(0, current_dir)
        import item_data
        ITEMS = item_data.ITEMS
        ITEM_CATEGORIES = getattr(item_data, 'CATEGORIES', [])
        if not ITEM_CATEGORIES:
            ITEM_CATEGORIES = list(set([item.get('category', 'その他') for item in ITEMS.values()]))
            ITEM_CATEGORIES.sort()
        print(f"✅ item_data.py 読み込み成功(方法2): {len(ITEMS)}個")
    except Exception as e2:
        print(f"❌ item_data.py 読み込み失敗: {e2}")

# command_data.py の読み込み
try:
    from command_data import COMMANDS as LOADED_COMMANDS
    COMMANDS = LOADED_COMMANDS
    
    try:
        from command_data import COMMAND_CATEGORIES
    except (ImportError, AttributeError):
        COMMAND_CATEGORIES = list(set([cmd.get('category', 'その他') for cmd in COMMANDS]))
        COMMAND_CATEGORIES.sort()
    
    print(f"✅ command_data.py 読み込み成功: {len(COMMANDS)}個")
    
except ImportError as e:
    print(f"❌ command_data.py インポートエラー: {e}")
    
    # 方法2: sys.pathを使った読み込み
    try:
        sys.path.insert(0, current_dir)
        import command_data
        COMMANDS = command_data.COMMANDS
        COMMAND_CATEGORIES = getattr(command_data, 'COMMAND_CATEGORIES', [])
        if not COMMAND_CATEGORIES:
            COMMAND_CATEGORIES = list(set([cmd.get('category', 'その他') for cmd in COMMANDS]))
            COMMAND_CATEGORIES.sort()
        print(f"✅ command_data.py 読み込み成功(方法2): {len(COMMANDS)}個")
    except Exception as e2:
        print(f"❌ command_data.py 読み込み失敗: {e2}")

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

# ========== コマンド検索関数 ==========
def search_commands(query, edition):
    """
    ユーザーの入力からコマンドを検索
    
    Args:
        query (str): 検索キーワード
        edition (str): Minecraftエディション（統合版/Java版）
    
    Returns:
        list: マッチしたコマンドのリスト
    """
    if not COMMANDS:
        return []
    
    results = []
    query_lower = query.lower()
    
    for cmd in COMMANDS:
        # キーワードマッチング
        if any(keyword.lower() in query_lower for keyword in cmd.get('keywords', [])):
            cmd_copy = cmd.copy()
            
            # アイテムIDの置換が必要な場合
            if '{item_id}' in cmd_copy.get('cmd_template', ''):
                if ITEMS:
                    # デフォルトアイテムを設定（最初のアイテム）
                    default_item = list(ITEMS.values())[0]
                    cmd_copy['cmd'] = cmd_copy['cmd_template'].replace(
                        '{item_id}', 
                        default_item['id'][edition]
                    )
                    cmd_copy['item_name'] = default_item['name']
                    cmd_copy['desc'] = cmd_copy.get('desc', '').replace('{item}', default_item['name'])
                else:
                    cmd_copy['cmd'] = cmd_copy['cmd_template']
            else:
                cmd_copy['cmd'] = cmd_copy.get('cmd_template', '')
            
            results.append(cmd_copy)
    
    return results

# ========== アイテム検索関数 ==========
def search_items(query, category=None):
    """
    アイテムを検索
    
    Args:
        query (str): 検索キーワード
        category (str): カテゴリフィルター
    
    Returns:
        dict: マッチしたアイテムの辞書
    """
    if not ITEMS:
        return {}
    
    filtered = ITEMS
    
    # キーワード検索
    if query:
        filtered = {
            k: v for k, v in filtered.items() 
            if query.lower() in v.get('name', '').lower()
        }
    
    # カテゴリフィルター
    if category and category != "全て":
        filtered = {
            k: v for k, v in filtered.items()
            if v.get('category') == category
        }
    
    return filtered

# ========== メイン画面 ==========

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

# データ読み込み状況を表示
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 データ状況")
st.sidebar.markdown(f"**アイテム:** {len(ITEMS)}個")
st.sidebar.markdown(f"**コマンド:** {len(COMMANDS)}個")
st.sidebar.markdown(f"**エディション:** {st.session_state.edition}")

# ========== ホーム画面 ==========
if menu == "🏠 ホーム":
    st.header("🏠 ホームメニュー")
    
    # デバッグ情報を表示
    with st.expander("🔍 デバッグ情報", expanded=False):
        st.markdown("**現在のディレクトリ:**")
        st.code(current_dir)
        st.markdown("**ディレクトリ内のファイル:**")
        st.code("\n".join(files_in_dir))
        st.markdown("**Pythonパス:**")
        st.code("\n".join(sys.path[:5]))
    
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
    
    # データ読み込み状況
    if ITEMS and COMMANDS:
        st.success(f"✅ データ読み込み成功: アイテム{len(ITEMS)}個、コマンド{len(COMMANDS)}個")
    else:
        st.warning("⚠️ データファイルが正しく読み込まれていません")
        st.info("💡 item_data.py と command_data.py が同じディレクトリにあることを確認してください")

# ========== コマンド生成画面 ==========
elif menu == "🛠 コマンド生成":
    st.header("🛠 コマンド生成")
    
    if not COMMANDS:
        st.error("❌ コマンドデータが読み込まれていません")
        st.stop()
    
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
                with st.expander(f"📋 {cmd.get('desc', 'コマンド')}", expanded=(i==0)):
                    st.code(cmd.get('cmd', ''), language='bash')
                    
                    # アイテム選択（必要な場合のみ）
                    if '{item_id}' in cmd.get('cmd_template', '') and ITEMS:
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
                    
                    st.markdown(f"**解説:** {cmd.get('desc', '')}")
                    if 'note' in cmd:
                        st.markdown(f"**補足:** {cmd['note']}")
                    if 'category' in cmd:
                        st.markdown(f"**カテゴリ:** {cmd['category']}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.markdown("**ヒント:** 以下のキーワードを試してください")
            # 利用可能なキーワードを表示
            all_keywords = set()
            for cmd in COMMANDS:
                all_keywords.update(cmd.get('keywords', []))
            sample_keywords = list(all_keywords)[:10]
            for keyword in sample_keywords:
                st.markdown(f"- {keyword}")

# ========== アイテム図鑑 ==========
elif menu == "📘 アイテム図鑑":
    st.header("📘 アイテム図鑑")
    
    if not ITEMS:
        st.error("❌ アイテムデータが読み込まれていません")
        st.stop()
    
    st.markdown("### アイテム一覧")
    
    # カテゴリフィルターと検索
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input("🔍 アイテムを検索", placeholder="例: ダイヤ、鉄")
    with col2:
        selected_category = st.selectbox(
            "カテゴリ",
            ["全て"] + ITEM_CATEGORIES,
            key="item_category"
        )
    
    # アイテム検索
    filtered_items = search_items(search_query, selected_category)
    
    if filtered_items:
        st.info(f"📦 {len(filtered_items)}個のアイテムが見つかりました")
        
        for item_key, item in filtered_items.items():
            category = item.get('category', 'その他')
            with st.expander(f"📦 {item.get('name', item_key)} [{category}]", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**統合版ID:**")
                    st.code(item['id'].get('統合版', 'N/A'))
                with col2:
                    st.markdown(f"**Java版ID:**")
                    st.code(item['id'].get('Java版', 'N/A'))
                
                # giveコマンドのサンプル
                st.markdown("**取得コマンド:**")
                give_cmd = f"/give @s {item['id'].get(st.session_state.edition, '')} 1"
                st.code(give_cmd, language='bash')
    else:
        st.warning("該当するアイテムが見つかりませんでした")

# ========== コマンド図鑑 ==========
elif menu == "🧾 コマンド図鑑":
    st.header("🧾 コマンド図鑑")
    
    if not COMMANDS:
        st.error("❌ コマンドデータが読み込まれていません")
        st.stop()
    
    st.markdown("### よく使うコマンド一覧")
    
    # カテゴリフィルター
    selected_cmd_category = st.selectbox(
        "カテゴリで絞り込み",
        ["全て"] + COMMAND_CATEGORIES,
        key="command_category"
    )
    
    filtered_commands = COMMANDS
    if selected_cmd_category != "全て":
        filtered_commands = [
            cmd for cmd in COMMANDS 
            if cmd.get('category') == selected_cmd_category
        ]
    
    st.info(f"📌 {len(filtered_commands)}個のコマンドが見つかりました")
    
    for i, cmd in enumerate(filtered_commands):
        category_tag = cmd.get('category', 'その他')
        with st.expander(f"📌 [{category_tag}] {cmd.get('desc', 'コマンド')}", expanded=False):
            st.code(cmd.get('cmd_template', ''), language='bash')
            st.markdown(f"**解説:** {cmd.get('desc', '')}")
            if 'note' in cmd:
                st.markdown(f"**補足:** {cmd['note']}")
            if 'keywords' in cmd:
                st.markdown(f"**検索キーワード:** {', '.join(cmd['keywords'])}")

# ========== 設定画面 ==========
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
    st.markdown("### 📊 データファイル情報")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("アイテム数", f"{len(ITEMS)}個")
        st.metric("アイテムカテゴリ", f"{len(ITEM_CATEGORIES)}種類")
    with col2:
        st.metric("コマンド数", f"{len(COMMANDS)}個")
        st.metric("コマンドカテゴリ", f"{len(COMMAND_CATEGORIES)}種類")
    
    st.markdown("---")
    st.markdown("### 📁 ファイル構成")
    st.code("""
プロジェクトフォルダ/
├── app.py (このファイル)
├── item_data.py (アイテムデータ)
└── command_data.py (コマンドデータ)
    """)
    
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
