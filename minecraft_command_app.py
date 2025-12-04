import streamlit as st
from pathlib import Path
import sys
import os
import importlib.util
import json

# Gemini APIの設定
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, 'secrets') else os.getenv("GEMINI_API_KEY")
# v1betaに戻す
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

# 正規化プロンプト
NORMALIZATION_PROMPT = """あなたはMinecraftのコマンド生成システムの自然言語正規化エンジンです。
ユーザーの曖昧な入力を、明確な構造化された形式に変換してください。

【出力形式】
「[対象]に[アイテム名/効果名]を[数量]個与える」または「[対象]に[効果名]の効果を付ける」

【対象の種類】
- 自分/me/@p/私/僕/俺 → 自分
- あいつ/他の人/ほかのプレイヤー/あの人/彼/彼女/@a → 他のプレイヤー
- みんな/全員/all/@a → 全プレイヤー
- 最も近い人/@r → 最も近いプレイヤー
- 特定のプレイヤー名(例: Steve, Alex) → [プレイヤー名]
- 対象が省略されている場合 → 自分

【数量の表現】
- 大量に/たくさん/いっぱい → 64個
- 1スタック/スタック → 64個
- 少し/数個/ちょっと → 5個
- 半スタック → 32個
- 具体的な数値があればその数値
- 省略時 → 1個(ただし松明など消耗品は10個)

【Minecraft用語マッピング】
■道具
- 掘るやつ/採掘道具/ツルハシ/つるはし/ピッケル/pick → ピッケル
- 斧/木切るの/伐採道具 → 斧
- 釣り竿/魚釣りたい → 釣り竿
- 水汲むやつ/バケツ → バケツ
- シャベル/スコップ → シャベル

■武器・防具
- 武器/攻撃できるやつ/剣的なの/けん → 剣
- 遠距離武器/弓矢/bow → 弓
- 防具一式/armor/鎧全部 → ヘルメット、チェストプレート、レギンス、ブーツ
- 頭装備/兜/ヘルメット的なやつ → ヘルメット

■ブロック・素材
- 木材/wood/木のブロック → 木材
- 石ころ/cobblestone/丸石 → 丸石
- 光るやつ/明かり/たいまつ/松明/たいまち → 松明
- 土/dirt/土ブロック → 土
- ガラス/透明なブロック → ガラス

■食料
- 食べ物/food/腹減った → パン
- 肉/ステーキ/beef → ステーキ
- パン/bread → パン
- 果物/リンゴ/apple → リンゴ

■特殊アイテム
- 爆弾/爆発するやつ → TNT
- ワープ/瞬間移動アイテム → エンダーパール
- 寝るやつ/respawn地点 → ベッド
- 時計/時間見るやつ/clock → 時計
- 地図/マッピング/map → 地図

■エフェクト（移動・身体能力）
- 足速くして/走りたい/speed/俊敏 → 俊敏
- 高く飛びたい/ジャンプ力up/jump boost → 跳躍
- 遅くして/のろま/slowness → 鈍化
- 泳ぎ速く/水中移動 → 水中移動

■エフェクト（戦闘関連）
- 強くなりたい/攻撃力up/strength/筋力 → 力
- 硬くなりたい/防御/resistance/耐性 → 耐性
- 再生/回復/regeneration/体力戻して → 再生
- 透明になりたい/invisible/見えなく → 透明化
- 光りたい/暗視/night vision/夜見える → 暗視

■エフェクト（その他）
- 水中呼吸/溺れない/water breathing → 水中呼吸
- 落下ダメージなし/軽やか → 低速落下
- 火耐性/fire resistance/燃えない/耐火 → 火炎耐性
- 毒/poison → 毒
- 弱体化/weakness/弱く → 弱体化

■素材の種類
- 木/wooden/wood → 木
- 石/stone → 石
- 鉄/iron/アイアン → 鉄
- 金/golden/gold/ゴールド → 金
- ダイヤ/ダイア/diamond/dia → ダイヤモンド
- ネザライト/netherite → ネザライト

【変換ルール】
1. 対象を特定し、必ず出力に含める
2. 「〜に」「〜へ」で対象を判別
3. 「やる」「あげる」「渡す」「くれ」「ください」→「与える」
4. 「〜したい」「〜になりたい」→「〜の効果を付ける」(対象は自分)
5. 数量を明示的に出力
6. 素材+アイテムの組み合わせは「[素材]の[アイテム]」
7. 防具一式は4つのパーツに展開(それぞれに対象と数量を付ける)
8. 複数要求は「、」で区切る
9. 対象が明示されていない場合は「自分」とする

【注意事項】
- 必ず「[対象]に」を含める
- 数量は必ず明示(「〜個」の形式)
- 対象が複数の場合も「、」で区切って個別に出力
- プレイヤー名が指定されている場合はそのまま使用
- 「自分」「他のプレイヤー」「全プレイヤー」「最も近いプレイヤー」のいずれかに統一
- 正規化された出力のみを返し、説明文は不要

【入力】
{user_input}

【正規化された出力】"""

# ========== Gemini API呼び出し関数 ==========
async def normalize_with_gemini(user_input):
    """
    Gemini APIを使ってユーザー入力を正規化
    """
    if not GEMINI_API_KEY:
        return None
    
    import aiohttp
    
    try:
        prompt = NORMALIZATION_PROMPT.replace("{user_input}", user_input)
        
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500,
            }
        }
        
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    result = await response.json()
                    
                    # テキスト抽出
                    candidates = result.get("candidates", [])
                    if candidates and len(candidates) > 0:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts and len(parts) > 0:
                            normalized_text = parts[0].get("text", "").strip()
                            return normalized_text
                    
                    return None
                else:
                    st.error(f"API Error {response.status}: {response_text}")
                    return None
                    
    except aiohttp.ClientError as e:
        st.error(f"接続エラー: {e}")
        return None
    except Exception as e:
        st.error(f"Gemini API エラー: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

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
if 'use_ai_normalization' not in st.session_state:
    st.session_state.use_ai_normalization = True
if 'normalized_text' not in st.session_state:
    st.session_state.normalized_text = ''

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
                    # クエリからアイテムを検索
                    matched_item = None
                    
                    # 1. アイテム名での完全一致検索
                    for item_key, item_data in ITEMS.items():
                        item_name = item_data.get('name', '').lower()
                        if item_name in query_lower:
                            matched_item = item_data
                            break
                    
                    # 2. エイリアスでの検索
                    if not matched_item:
                        for item_key, item_data in ITEMS.items():
                            aliases = item_data.get('aliases', [])
                            for alias in aliases:
                                if alias.lower() in query_lower:
                                    matched_item = item_data
                                    break
                            if matched_item:
                                break
                    
                    # 3. マッチしない場合はデフォルト（最初のアイテム）
                    if not matched_item:
                        matched_item = list(ITEMS.values())[0]
                    
                    # アイテムIDの取得
                    item_id_data = matched_item.get('id', {})
                    if isinstance(item_id_data, dict):
                        item_id = item_id_data.get(edition, '')
                    else:
                        item_id = item_id_data
                    
                    cmd_copy['cmd'] = cmd_template.replace('{item_id}', item_id)
                    cmd_copy['item_name'] = matched_item.get('name', '')
                    cmd_copy['matched_item_key'] = item_key
                    
                    # 説明文のアイテム名も置換
                    desc = cmd_copy.get('desc', '')
                    if '{item}' in desc:
                        cmd_copy['desc'] = desc.replace('{item}', matched_item.get('name', ''))
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
    
    # AI正規化の設定
    col_ai1, col_ai2 = st.columns([3, 1])
    with col_ai1:
        st.markdown("### やりたいことを自然な日本語で入力してください")
    with col_ai2:
        use_ai = st.toggle(
            "🤖 AI正規化",
            value=st.session_state.use_ai_normalization,
            help="Gemini APIで自然言語を理解します",
            key="ai_toggle"
        )
        st.session_state.use_ai_normalization = use_ai
    
    # API キーの確認
    if use_ai and not GEMINI_API_KEY:
        st.warning("⚠️ Gemini APIキーが設定されていません。Streamlit Secretsに`GEMINI_API_KEY`を追加してください。")
        st.info("AI正規化なしで動作します。")
        use_ai = False
    
    user_input = st.text_area(
        "入力例",
        value=st.session_state.user_input,
        placeholder="例:\n- パンが欲しい\n- 足を速くしたい\n- ダイヤのツルハシちょうだい\n- みんなに松明を大量に配る",
        height=100,
        key="command_input"
    )
    
    # 処理ボタン
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        generate_btn = st.button("🚀 コマンド生成", type="primary", use_container_width=True)
    
    if generate_btn and user_input:
        st.session_state.user_input = user_input
        
        # AI正規化を使用する場合
        if use_ai:
            with st.spinner("🤖 AIが入力を理解しています..."):
                import asyncio
                
                # デバッグモード
                with st.expander("🔍 デバッグ情報", expanded=False):
                    st.markdown("**送信するプロンプト:**")
                    debug_prompt = NORMALIZATION_PROMPT.replace("{user_input}", user_input)
                    st.code(debug_prompt[:500] + "..." if len(debug_prompt) > 500 else debug_prompt)
                
                normalized = asyncio.run(normalize_with_gemini(user_input))
                
                if normalized:
                    st.session_state.normalized_text = normalized
                    st.success("✅ AI正規化完了")
                    st.info(f"**理解した内容:** {normalized}")
                    
                    # 正規化されたテキストでコマンド検索
                    search_text = normalized
                else:
                    st.warning("⚠️ AI正規化に失敗しました。元の入力で検索します。")
                    st.info("💡 プロンプトを調整するか、APIキーを確認してください")
                    search_text = user_input
        else:
            search_text = user_input
        
        # コマンド検索
        candidates = search_commands(search_text, st.session_state.edition)
        
        if candidates:
            st.success(f"✅ {len(candidates)}件のコマンドが見つかりました")
            
            for i, cmd in enumerate(candidates):
                cmd_name = cmd.get('name', cmd.get('desc', 'コマンド'))
                item_name = cmd.get('item_name', '')
                
                # タイトル表示
                if item_name:
                    expander_title = f"📋 {cmd_name}: {item_name}を与える"
                else:
                    expander_title = f"📋 {cmd_name}: {cmd.get('desc', '')}"
                
                with st.expander(expander_title, expanded=(i==0)):
                    st.code(cmd.get('cmd', ''), language='bash')
                    
                    # アイテム選択（必要な場合のみ）
                    if '{item_id}' in cmd.get('cmd_template', '') and ITEMS:
                        st.markdown("---")
                        st.markdown("**🔄 アイテムを変更:**")
                        
                        # 現在選択されているアイテムをデフォルトに
                        current_item_key = cmd.get('matched_item_key', list(ITEMS.keys())[0])
                        item_names = [item.get('name', k) for k, item in ITEMS.items()]
                        current_item_name = ITEMS.get(current_item_key, {}).get('name', item_names[0])
                        
                        try:
                            default_index = item_names.index(current_item_name)
                        except ValueError:
                            default_index = 0
                        
                        selected_item = st.selectbox(
                            "アイテム選択",
                            options=item_names,
                            index=default_index,
                            key=f"item_select_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # アイテム変更時にコマンドを更新
                        for item_key, item in ITEMS.items():
                            if item.get('name', item_key) == selected_item:
                                item_id_data = item.get('id', {})
                                if isinstance(item_id_data, dict):
                                    item_id = item_id_data.get(st.session_state.edition, item_key)
                                else:
                                    item_id = item_id_data
                                updated_cmd = cmd['cmd_template'].replace('{item_id}', item_id)
                                st.code(updated_cmd, language='bash')
                                break
                    
                    st.markdown("---")
                    st.markdown(f"**📝 解説:** {cmd.get('desc', '')}")
                    if 'note' in cmd and cmd['note']:
                        st.markdown(f"**💡 補足:** {cmd['note']}")
                    if 'category' in cmd:
                        st.markdown(f"**🏷️ カテゴリ:** {cmd['category']}")
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
    st.markdown("### 🤖 AI機能設定")
    
    st.markdown("**Gemini API キー**")
    if GEMINI_API_KEY:
        st.success("✅ APIキーが設定されています")
    else:
        st.warning("⚠️ APIキーが未設定です")
        st.info("Streamlit Cloudの場合: Settings → Secrets に `GEMINI_API_KEY = 'your-api-key'` を追加")
        st.info("ローカルの場合: 環境変数 `GEMINI_API_KEY` を設定")
    
    with st.expander("📖 Gemini APIキーの取得方法"):
        st.markdown("""
        1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
        2. 「Get API Key」をクリック
        3. APIキーをコピー
        4. Streamlit Secretsまたは環境変数に設定
        """)
    
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
