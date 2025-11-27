"""
コマンド生成ロジック
"""

def generate_command(cmd_template, edition, **kwargs):
    """
    コマンドテンプレートから実際のコマンドを生成
    
    Args:
        cmd_template: コマンドテンプレート文字列
        edition: エディション('統合版' or 'Java版')
        **kwargs: テンプレート変数(item_id, effect_id, etc.)
    
    Returns:
        str: 生成されたコマンド
    """
    command = cmd_template
    
    # テンプレート変数を置換
    for key, value in kwargs.items():
        placeholder = f"{{{key}}}"
        if placeholder in command:
            command = command.replace(placeholder, str(value))
    
    return command


def validate_command(command):
    """
    コマンドの基本的な妥当性をチェック
    
    Args:
        command: チェックするコマンド文字列
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not command:
        return (False, "コマンドが空です")
    
    if not command.startswith('/'):
        return (False, "コマンドは'/'で始まる必要があります")
    
    # 未置換のプレースホルダーをチェック
    if '{' in command and '}' in command:
        return (False, "未置換のパラメータがあります")
    
    return (True, "")


def format_command_display(command, add_color=True):
    """
    コマンドを表示用にフォーマット
    
    Args:
        command: コマンド文字列
        add_color: シンタックスハイライト用のHTMLを追加するか
    
    Returns:
        str: フォーマット済みコマンド
    """
    if not add_color:
        return command
    
    # シンプルなシンタックスハイライト
    parts = command.split()
    formatted_parts = []
    
    for i, part in enumerate(parts):
        if i == 0:  # コマンド名
            formatted_parts.append(f'<span style="color: #00FF00;">{part}</span>')
        elif part.startswith('@'):  # セレクタ
            formatted_parts.append(f'<span style="color: #FFD700;">{part}</span>')
        elif part.startswith('-') or part.startswith('~'):  # 座標
            formatted_parts.append(f'<span style="color: #87CEEB;">{part}</span>')
        elif part.isdigit():  # 数値
            formatted_parts.append(f'<span style="color: #FF69B4;">{part}</span>')
        else:
            formatted_parts.append(part)
    
    return ' '.join(formatted_parts)


def get_command_examples(cmd_key, commands_dict, edition):
    """
    特定のコマンドの使用例を取得
    
    Args:
        cmd_key: コマンドキー
        commands_dict: コマンド辞書
        edition: エディション
    
    Returns:
        list: 使用例のリスト
    """
    if cmd_key not in commands_dict:
        return []
    
    cmd_data = commands_dict[cmd_key]
    template = cmd_data['template'].get(edition, '')
    
    examples = []
    
    # テンプレートがリストの場合
    if isinstance(template, list):
        examples = template
    else:
        examples = [template]
    
    return examples


def suggest_similar_commands(user_input, commands_dict, threshold=0.3):
    """
    類似したコマンドを提案
    
    Args:
        user_input: ユーザー入力
        commands_dict: コマンド辞書
        threshold: 類似度の閾値
    
    Returns:
        list: 提案コマンドのリスト
    """
    suggestions = []
    user_lower = user_input.lower()
    
    for cmd_key, cmd_data in commands_dict.items():
        score = 0
        
        # 名前との類似度
        if user_lower in cmd_data['name'].lower():
            score += 0.5
        
        # 説明との類似度
        if user_lower in cmd_data['desc'].lower():
            score += 0.3
        
        # エイリアスとの類似度
        for alias in cmd_data.get('aliases', []):
            if user_lower in alias.lower():
                score += 0.4
                break
        
        if score >= threshold:
            suggestions.append({
                'cmd_key': cmd_key,
                'cmd_data': cmd_data,
                'score': score
            })
    
    # スコア順にソート
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return suggestions[:5]  # 上位5件
