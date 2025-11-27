import streamlit as st
from pathlib import Path
import sys

# ========== 外部ファイルの読み込み ==========
import os
import importlib.util

# 現在のディレクトリとファイル一覧を確認
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
files_in_dir = os.listdir(current_dir)

# データ読み込み
ITEMS = {}
ITEM_CATEGORIES = []
COMMANDS = []
COMMAND_CATEGORIES = []

load_status = {
    'items': False,
    'commands': False,
    'items_error': '',
    'commands_error': ''
}

# item_data.py の読み込み
try:
    item_data_path = os.path.join(current_dir, 'item_data.py')
    
    if os.path.exists(item_data_path):
        spec = importlib.util.spec_from_file_location("item_data", item_data_path)
        item_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(item_data)
        
        # items辞書を読み込む（小文字のitemsに対応）
        items_dict = getattr(item_data, 'items', None) or getattr(item_data, 'ITEMS', {})
        
        # 辞書形式をそのまま使用
        ITEMS = items_dict
        
        # カテゴリ情報の取得
        ITEM_CATEGORIES = getattr(item_data, 'categories', None) or getattr(item_data, 'CATEGORIES', [])
        
        if not ITEM_CATEGORIES and ITEMS:
            ITEM_CATEGORIES = list(set([item.get('category', 'その他') for item in ITEMS.values()]))
            ITEM_CATEGORIES.sort()
        
        load_status['items'] = True
        load_status['items_count'] = len(ITEMS)
    else:
        load_status['items_error'] = f"ファイルが見つかりません: {item_data_path}"
        
except Exception as e:
    load_status['items_error'] = str(e)

# command_data.py の読み込み（辞書形式に対応）
try:
    command_data_path = os.path.join(current_dir, 'command_data.py')
    
    if os.path.exists(command_data_path):
        spec = importlib.util.spec_from_file_location("command_data", command_data_path)
        command_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command_data)
        
        # commands辞書を読み込んで、リスト形式に変換
        commands_dict = getattr(command_data, 'commands', None) or getattr(command_data, 'COMMANDS', [])
        
        if isinstance(commands_dict, dict):
            # 辞書形式を内部用のリスト形式に変換
            COMMANDS = []
            for cmd_key, cmd_data in commands_dict.items():
                command_entry = {
                    'key': cmd_key,
                    'name': cmd_data.get('name', cmd_key),
                    'desc': cmd_data.get('desc', ''),
                    'keywords': cmd_data.get('aliases', []),
                    'template': cmd_data.get('template', {}),
                    'note': cmd_data.get('note', ''),
                    'category': cmd_data.get('category', 'その他')
                }
                COMMANDS.append(command_entry)
        elif isinstance(commands_dict, list):
            COMMANDS = commands_dict
        
        # template_requires_item関数も読み込む
        template_requires_item = getattr(command_data, 'template_requires_item', None)
        
        COMMAND_CATEGORIES = list(set([cmd.get('category', 'その他') for cmd in COMMANDS]))
        COMMAND_CATEGORIES.sort()
        
        load_status['commands'] = True
        load_status['commands_count'] = len(COMMANDS)
    else:
        load_status['commands_error'] = f"ファイルが見つかりません: {command_data_path}"
        
except Exception as e:
    load_status['commands_error'] = str(e)

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
        # キーワードマッチング（aliases/keywordsの両方に対応）
        keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
        if any(keyword.lower() in query_lower for keyword in keywords):
            cmd_copy = cmd.copy()
            
            # テンプレートの取得
            template = cmd_copy.get('template', {})
            
            # エディション別のテンプレートを取得
            if isinstance(template, dict):
                cmd_template = template.get(edition, '')
                # リスト形式の場合は最初の要素を使用
                if isinstance(cmd_template, list):
                    cmd_template = cmd_template[0] if cmd_template else ''
            else:
                cmd_template = template
            
            # アイテムIDの置換が必要な場合
            if '{item_id}' in str(cmd_template):
                if ITEMS:
                    # デフォルトアイテムを設定
                    default_item = list(ITEMS.values())[0]
                    default_item_id = default_item.get('id', {}).get(edition, default_item.get('name', ''))
                    cmd_copy['cmd'] = cmd_template.replace('{item_id}', default_item_id)
                    cmd_copy['item_name'] = default_item.get('name', '')
                    # 説明文のアイテム名も置換
                    desc = cmd_copy.get('desc', '')
                    if '{item}' in desc:
                        cmd_copy['desc'] = desc.replace('{item}', default_item.get('name', ''))
                else:
                    cmd_copy['cmd'] = cmd_template
            else:
                cmd_copy['cmd'] = cmd_template
            
            # cmd_templateを保持（後でアイテム変更に使用）
            cmd_copy['cmd_template'] = cmd_template
            
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
    
    # キーワード検索（名前とaliasesの両方を検索）
    if query:
        query_lower = query.lower()
        filtered = {}
        for k, v in ITEMS.items():
            # 名前での検索
            if query_lower in v.get('name', '').lower():
                filtered[k] = v
                continue
            # aliasesでの検索
            aliases = v.get('aliases', [])
            if any(query_lower in alias.lower() for alias in aliases):
                filtered[k] = v
                continue
    
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
    
    # データ読み込み状況を表示
    if load_status['items'] and load_status['commands']:
        st.success(f"✅ データ読み込み成功！")
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.metric("アイテム数", f"{len(ITEMS)}個")
        with col_info2:
            st.metric("コマンド数", f"{len(COMMANDS)}個")
    else:
        st.error("⚠️ データファイルの読み込みに問題があります")
        
        if not load_status['items']:
            st.warning(f"❌ item_data.py: {load_status['items_error']}")
        else:
            st.success(f"✅ item_data.py: {len(ITEMS)}個読み込み成功")
            
        if not load_status['commands']:
            st.warning(f"❌ command_data.py: {load_status['commands_error']}")
        else:
            st.success(f"✅ command_data.py: {len(COMMANDS)}個読み込み成功")
    
    # デバッグ情報を表示
    with st.expander("🔍 デバッグ情報（開発者向け）", expanded=False):
        st.markdown("**現在のディレクトリ:**")
        st.code(current_dir)
        st.markdown("**ディレクトリ内のファイル:**")
        st.code("\n".join(sorted(files_in_dir)))
        st.markdown("**データファイルの存在確認:**")
        st.code(f"item_data.py: {os.path.exists(os.path.join(current_dir, 'item_data.py'))}")
        st.code(f"command_data.py: {os.path.exists(os.path.join(current_dir, 'command_data.py'))}")
    
    st.markdown("---")
    
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
        st.success(f"✅ すべてのデータが正常に読み込まれています")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.info(f"📦 アイテム: {len(ITEMS)}個")
        with col_stat2:
            st.info(f"📋 コマンド: {len(COMMANDS)}個")
    else:
        st.warning("⚠️ 一部のデータが読み込まれていません")
        if not ITEMS:
            st.error(f"❌ item_data.py: {load_status.get('items_error', '不明なエラー')}")
        if not COMMANDS:
            st.error(f"❌ command_data.py: {load_status.get('commands_error', '不明なエラー')}")

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
                cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
                with st.expander(f"📋 {cmd_name}: {cmd.get('desc', '')}", expanded=(i==0)):
                    st.code(cmd.get('cmd', ''), language='bash')
                    
                    # アイテム選択（必要な場合のみ）
                    if '{item_id}' in cmd.get('cmd_template', '') and ITEMS:
                        st.markdown("**アイテムを変更:**")
                        selected_item = st.selectbox(
                            "アイテム選択",
                            options=[item.get('name', k) for k, item in ITEMS.items()],
                            key=f"item_select_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # アイテム変更時にコマンドを更新
                        for item_key, item in ITEMS.items():
                            if item.get('name', item_key) == selected_item:
                                item_id = item.get('id', {}).get(st.session_state.edition, selected_item)
                                updated_cmd = cmd['cmd_template'].replace('{item_id}', item_id)
                                st.code(updated_cmd, language='bash')
                                break
                    
                    st.markdown(f"**解説:** {cmd.get('desc', '')}")
                    if 'note' in cmd and cmd['note']:
                        st.markdown(f"**補足:** {cmd['note']}")
                    if 'category' in cmd:
                        st.markdown(f"**カテゴリ:** {cmd['category']}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.markdown("**ヒント:** 以下のキーワードを試してください")
            # 利用可能なキーワードを表示
            all_keywords = set()
            for cmd in COMMANDS:
                keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
                all_keywords.update(keywords)
            sample_keywords = list(all_keywords)[:15]
            cols = st.columns(3)
            for idx, keyword in enumerate(sample_keywords):
                with cols[idx % 3]:
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
        search_query = st.text_input(
            "🔍 アイテムを検索", 
            placeholder="例: 木、オーク、板材",
            help="アイテム名やエイリアス（別名）で検索できます"
        )
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
            item_name = item.get('name', item_key)
            item_desc = item.get('desc', '')
            
            # エイリアス（別名）の取得
            aliases = item.get('aliases', [])
            alias_display = f"別名: {', '.join(aliases[:5])}" if aliases else ""
            if len(aliases) > 5:
                alias_display += f"...他{len(aliases)-5}個"
            
            with st.expander(f"📦 {item_name} [{category}]", expanded=False):
                if item_desc:
                    st.markdown(f"**説明:** {item_desc}")
                
                col1, col2 = st.columns(2)
                
                # IDの取得
                item_id_data = item.get('id', {})
                
                with col1:
                    st.markdown(f"**統合版ID:**")
                    if isinstance(item_id_data, dict):
                        bedrock_id = item_id_data.get('統合版', item_key)
                    else:
                        bedrock_id = item_id_data
                    st.code(bedrock_id)
                    
                with col2:
                    st.markdown(f"**Java版ID:**")
                    if isinstance(item_id_data, dict):
                        java_id = item_id_data.get('Java版', f'minecraft:{item_key}')
                    else:
                        java_id = item_id_data
                    st.code(java_id)
                
                # スタックサイズ
                stack_size = item.get('stack_size', 64)
                st.markdown(f"**スタックサイズ:** {stack_size}")
                
                # エイリアス表示
                if aliases:
                    with st.expander("🏷️ 検索用エイリアス", expanded=False):
                        st.markdown(", ".join(aliases))
                
                # giveコマンドのサンプル
                st.markdown("**取得コマンド:**")
                current_id = bedrock_id if st.session_state.edition == '統合版' else java_id
                
                col_cmd1, col_cmd2 = st.columns(2)
                with col_cmd1:
                    st.markdown("*1個:*")
                    give_cmd_1 = f"/give @s {current_id} 1"
                    st.code(give_cmd_1, language='bash')
                with col_cmd2:
                    st.markdown(f"*{stack_size}個:*")
                    give_cmd_stack = f"/give @s {current_id} {stack_size}"
                    st.code(give_cmd_stack, language='bash')
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
        cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
        
        # テンプレートの取得
        template = cmd.get('template', {})
        if isinstance(template, dict):
            cmd_template = template.get(st.session_state.edition, '')
            if isinstance(cmd_template, list):
                cmd_template = cmd_template[0] if cmd_template else ''
        else:
            cmd_template = template
        
        with st.expander(f"📌 [{category_tag}] {cmd_name}", expanded=False):
            st.code(cmd_template, language='bash')
            st.markdown(f"**解説:** {cmd.get('desc', '')}")
            if 'note' in cmd and cmd['note']:
                st.markdown(f"**補足:** {cmd['note']}")
            
            # キーワード表示
            keywords = cmd.get('keywords', []) or cmd.get('aliases', [])
            if keywords:
                st.markdown(f"**検索キーワード:** {', '.join(keywords[:10])}")
                if len(keywords) > 10:
                    st.markdown(f"*...他{len(keywords)-10}個*")

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
