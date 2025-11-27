"""
検索とフィルタリング機能
"""

def search_items(query, category=None, items_dict=None):
    """
    アイテムを検索する
    
    Args:
        query: 検索クエリ
        category: カテゴリフィルター
        items_dict: アイテム辞書
    
    Returns:
        list: マッチしたアイテムのリスト [(item_id, item_data), ...]
    """
    if not query and not category:
        return []
    
    query_lower = query.lower().strip() if query else ""
    results = []
    
    for item_id, item_data in items_dict.items():
        # カテゴリフィルター
        if category and item_data.get('category') != category:
            continue
        
        # クエリが空の場合はカテゴリのみでフィルタ
        if not query:
            results.append((item_id, item_data))
            continue
        
        # 検索マッチング
        matched = False
        
        # アイテムID検索
        if query_lower in item_id.lower():
            matched = True
        
        # アイテム名検索
        if query_lower in item_data['name'].lower():
            matched = True
        
        # 説明文検索
        if query_lower in item_data.get('desc', '').lower():
            matched = True
        
        # エイリアス検索
        aliases = item_data.get('aliases', [])
        if any(query_lower in alias.lower() for alias in aliases):
            matched = True
        
        if matched:
            results.append((item_id, item_data))
    
    return results


def search_commands(query, commands_dict):
    """
    コマンドを検索する
    
    Args:
        query: 検索クエリ
        commands_dict: コマンド辞書
    
    Returns:
        list: マッチしたコマンドのリスト [(cmd_key, cmd_data), ...]
    """
    if not query:
        return []
    
    query_lower = query.lower().strip()
    results = []
    
    for cmd_key, cmd_data in commands_dict.items():
        matched = False
        
        # コマンドキー検索
        if query_lower in cmd_key.lower():
            matched = True
        
        # コマンド名検索
        if query_lower in cmd_data['name'].lower():
            matched = True
        
        # 説明文検索
        if query_lower in cmd_data['desc'].lower():
            matched = True
        
        # エイリアス検索
        aliases = cmd_data.get('aliases', [])
        if any(query_lower in alias.lower() for alias in aliases):
            matched = True
        
        if matched:
            results.append((cmd_key, cmd_data))
    
    return results


def filter_by_keyword(user_input, edition, commands_dict, items_dict):
    """
    自然言語入力からコマンド候補を生成
    
    Args:
        user_input: ユーザーの入力文
        edition: エディション('統合版' or 'Java版')
        commands_dict: コマンド辞書
        items_dict: アイテム辞書
    
    Returns:
        list: コマンド候補のリスト
    """
    user_input_lower = user_input.lower().strip()
    candidates = []
    
    # コマンドを検索
    for cmd_key, cmd_data in commands_dict.items():
        # エイリアスでマッチング
        aliases = cmd_data.get('aliases', [])
        matched_aliases = [a for a in aliases if a.lower() in user_input_lower]
        
        if matched_aliases:
            template = cmd_data['template'].get(edition, '')
            
            # テンプレートがリストの場合は最初のものを使用
            if isinstance(template, list):
                template = template[0] if template else ''
            
            # アイテムIDが必要かチェック
            needs_item = '{item_id}' in template
            
            if needs_item:
                # アイテムも検索
                item_results = search_items(user_input, None, items_dict)
                
                if item_results:
                    # マッチしたアイテムごとに候補を生成
                    for item_id, item_data in item_results[:5]:  # 最大5件
                        item_name = item_data['name']
                        item_edition_id = item_data['id'].get(edition, '')
                        
                        if item_edition_id:
                            generated_cmd = template.replace('{item_id}', item_edition_id)
                            desc = cmd_data['desc'].replace('{item}', item_name)
                            
                            candidates.append({
                                'cmd': generated_cmd,
                                'desc': desc,
                                'note': cmd_data.get('note', ''),
                                'template': template,
                                'needs_item': True,
                                'item_name': item_name,
                                'display': f"{cmd_data['name']}: {desc}"
                            })
                else:
                    # アイテムが見つからない場合はテンプレートのみ
                    candidates.append({
                        'cmd': template,
                        'desc': cmd_data['desc'],
                        'note': cmd_data.get('note', ''),
                        'template': template,
                        'needs_item': True,
                        'display': f"{cmd_data['name']}: {cmd_data['desc']}"
                    })
            else:
                # アイテム不要なコマンド
                candidates.append({
                    'cmd': template,
                    'desc': cmd_data['desc'],
                    'note': cmd_data.get('note', ''),
                    'template': template,
                    'needs_item': False,
                    'display': f"{cmd_data['name']}: {cmd_data['desc']}"
                })
    
    return candidates


def get_item_by_name(item_name, items_dict):
    """
    アイテム名からアイテムデータを取得
    
    Args:
        item_name: アイテム名
        items_dict: アイテム辞書
    
    Returns:
        tuple: (item_id, item_data) or (None, None)
    """
    for item_id, item_data in items_dict.items():
        if item_data['name'] == item_name:
            return (item_id, item_data)
    return (None, None)
