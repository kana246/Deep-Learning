import streamlit as st
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from data.items import items
from data.commands import commands
from utils.search import search_items, search_commands, filter_by_keyword
from utils.generator import generate_command

# ページ設定
st.set_page_config(
    page_title="マイクラコマンド生成ツール",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4169E1;
        margin-top: 1rem;
    }
    .command-box {
        background-color: #1E1E1E;
        color: #00FF00;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
        margin: 1rem 0;
    }
    .item-card {
        border: 2px solid #4169E1;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #F0F8FF;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
        font-size: 1.1rem;
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
if 'selected_item' not in st.session_state:
    st.session_state.selected_item = None

# サイドバー
with st.sidebar:
    st.markdown("### ⚙️ 設定")
    st.session_state.edition = st.radio(
        "Minecraftバージョン",
        options=['統合版', 'Java版'],
        index=0 if st.session_state.edition == '統合版' else 1
    )
    
    st.markdown("---")
    st.markdown("### 📚 ナビゲーション")
    
    if st.button("🏠 ホーム", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
    
    if st.button("🎮 コマンド生成", use_container_width=True):
        st.session_state.page = 'command'
        st.rerun()
    
    if st.button("📘 アイテム図鑑", use_container_width=True):
        st.session_state.page = 'items'
        st.rerun()
    
    if st.button("🧾 コマンド一覧", use_container_width=True):
        st.session_state.page = 'command_list'
        st.rerun()

# ホームページ
if st.session_state.page == 'home':
    st.markdown('<div class="main-header">🎮 マイクラコマンド生成ツール</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🚀 主な機能")
        st.markdown("""
        - 🗣️ **自然言語でコマンド生成**  
          「ダイヤの剣がほしい」と入力するだけ！
          
        - 📘 **充実したアイテム図鑑**  
          全アイテムを検索・確認可能
          
        - 🎯 **統合版・Java版対応**  
          両バージョンに完全対応
          
        - ⚡ **即座にコピー可能**  
          生成されたコマンドをワンクリックでコピー
        """)
    
    with col2:
        st.markdown("### 📖 使い方")
        st.markdown("""
        1. サイドバーでバージョンを選択
        2. 「コマンド生成」をクリック
        3. やりたいことを日本語で入力
        4. 候補から選択してコマンドを生成
        5. コマンドをコピーして使用
        """)
    
    st.markdown("---")
    
    st.info(f"📌 現在の設定: **{st.session_state.edition}**")
    
    # クイックアクセス
    st.markdown("### ⚡ クイックアクセス")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 よく使うコマンド", use_container_width=True):
            st.session_state.page = 'command'
            st.rerun()
    
    with col2:
        if st.button("🔍 アイテム検索", use_container_width=True):
            st.session_state.page = 'items'
            st.rerun()
    
    with col3:
        if st.button("📋 コマンド例", use_container_width=True):
            st.session_state.page = 'command_list'
            st.rerun()

# コマンド生成ページ
elif st.session_state.page == 'command':
    st.markdown('<div class="main-header">🛠️ コマンド生成</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 入力エリア
    user_input = st.text_input(
        "やりたいことを日本語で入力してください",
        placeholder="例: ダイヤの剣がほしい、村人を召喚したい、飛びたい",
        help="自然な日本語で入力してください"
    )
    
    if user_input:
        # コマンド候補を検索
        candidates = filter_by_keyword(user_input, st.session_state.edition, commands, items)
        
        if candidates:
            st.success(f"✅ {len(candidates)}件の候補が見つかりました")
            
            # 候補を表示
            for idx, candidate in enumerate(candidates):
                with st.expander(f"💡 {candidate['display']}", expanded=(idx == 0)):
                    st.markdown(f"**説明**: {candidate['desc']}")
                    
                    # アイテムが必要な場合
                    if candidate.get('needs_item'):
                        item_names = [item['name'] for item in items.values()]
                        selected_item = st.selectbox(
                            "アイテムを選択",
                            options=item_names,
                            key=f"item_select_{idx}"
                        )
                        
                        # 選択されたアイテムのIDを取得
                        for item_id, item_data in items.items():
                            if item_data['name'] == selected_item:
                                selected_item_id = item_data['id'].get(st.session_state.edition, '')
                                break
                        
                        generated_cmd = candidate['template'].replace('{item_id}', selected_item_id)
                    else:
                        generated_cmd = candidate['cmd']
                    
                    # コマンド表示
                    st.markdown(f'<div class="command-box">{generated_cmd}</div>', unsafe_allow_html=True)
                    
                    # コピーボタン
                    if st.button(f"📋 コマンドをコピー", key=f"copy_{idx}"):
                        st.code(generated_cmd, language="bash")
                        st.success("✅ コマンドを表示しました！ゲーム内でコピー&ペーストしてください")
                    
                    if candidate.get('note'):
                        st.info(f"ℹ️ {candidate['note']}")
        else:
            st.warning("⚠️ 該当するコマンドが見つかりませんでした")
            st.markdown("""
            **ヒント:**
            - 「ダイヤがほしい」「村人を出したい」など、シンプルな表現で試してください
            - アイテム図鑑で正確な名前を確認できます
            """)

# アイテム図鑑ページ
elif st.session_state.page == 'items':
    st.markdown('<div class="main-header">📘 アイテム図鑑</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 検索バー
    search_query = st.text_input(
        "🔍 アイテムを検索",
        placeholder="アイテム名またはキーワードを入力"
    )
    
    # カテゴリフィルター
    categories = list(set([item.get('category', 'その他') for item in items.values()]))
    selected_category = st.selectbox("カテゴリ", options=['すべて'] + sorted(categories))
    
    # 検索結果
    if search_query or selected_category != 'すべて':
        results = search_items(search_query, selected_category if selected_category != 'すべて' else None, items)
        
        st.markdown(f"### 検索結果: {len(results)}件")
        
        # グリッド表示
        cols = st.columns(3)
        for idx, (item_id, item_data) in enumerate(results):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(f'<div class="item-card">', unsafe_allow_html=True)
                    st.markdown(f"**{item_data['name']}**")
                    st.caption(item_data.get('desc', '説明なし'))
                    
                    edition_id = item_data['id'].get(st.session_state.edition, 'N/A')
                    st.code(edition_id, language="text")
                    
                    if st.button(f"詳細を見る", key=f"detail_{item_id}"):
                        with st.expander("詳細情報", expanded=True):
                            st.markdown(f"**カテゴリ**: {item_data.get('category', '未分類')}")
                            st.markdown(f"**スタック数**: {item_data.get('stack_size', 64)}")
                            if item_data.get('aliases'):
                                st.markdown(f"**別名**: {', '.join(item_data['aliases'][:5])}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("🔍 検索ワードを入力するか、カテゴリを選択してください")

# コマンド一覧ページ
elif st.session_state.page == 'command_list':
    st.markdown('<div class="main-header">🧾 コマンド一覧</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    for cmd_key, cmd_data in commands.items():
        with st.expander(f"📌 {cmd_data['name']} - {cmd_data['desc']}"):
            st.markdown(f"**コマンドキー**: `{cmd_key}`")
            
            # テンプレート表示
            template = cmd_data['template'].get(st.session_state.edition, '')
            if isinstance(template, list):
                st.markdown("**テンプレート例:**")
                for t in template:
                    st.code(t, language="bash")
            else:
                st.code(template, language="bash")
            
            # エイリアス表示
            if cmd_data.get('aliases'):
                st.markdown(f"**検索キーワード**: {', '.join(cmd_data['aliases'][:10])}")
            
            if cmd_data.get('note'):
                st.info(f"ℹ️ {cmd_data['note']}")

# フッター
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: gray;">マイクラコマンド生成ツール - Powered by Streamlit</div>',
    unsafe_allow_html=True
)
