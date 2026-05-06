import os
import json
import time
import random
from openai import OpenAI
from datetime import datetime
from litellm import completion

log_buffer = []

def log_print(text):
    print(text)
    log_buffer.append(text)#書き出し用

os.environ["OPENAI_API_KEY"] = "your_api_key_here"
os.environ["ANTHROPIC_API_KEY"] = "your_api_key_here"
os.environ["GEMINI_API_KEY"] = "your_api_key_here"
os.environ["GROQ_API_KEY"] = "your_api_key_here"
os.environ["MISTRAL_API_KEY"] = "your_api_key_here"
os.environ["XAI_API_KEY"] = "your_api_key_here"

# ==========================================
# 1. 初期設定
# ==========================================
client = OpenAI()
# ==========================================
# 2. 参加キャラクター、お題、役職の定義
# ==========================================
def generate_game_setting():
    print("🎲 ゲームマスター(GPT)が絶妙なお題を考案中...")
    gm_prompt = """
    あなたはワードウルフのゲームマスターです。
    議論が白熱するような、絶妙なズレがある「秀逸なお題のペア」を1つだけ考えてください。
    条件：
    1. どちらも一般的な名詞であること（例：「海」と「プール」、「学校」と「病院」など）
    2. 出力は以下のJSONのみで行うこと。
    {
      "majority": "多数派のお題（市民用）",
      "minority": "少数派のお題（ウルフ用）"
    }
    """
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": gm_prompt}],
        temperature=0.8 
    )
    
    clean_text = response.choices[0].message.content
    clean_text = clean_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)
# お題を生成
theme = generate_game_setting()
log_print(f"✅ お題決定！ 市民:【{theme['majority']}】 / ウルフ:【{theme['minority']}】\n")

# ==========================================
# 2. 参加キャラクターランダム配役
# ==========================================
players = [
    {"name": "GPT", "model": "gpt-4o", "persona": "冷徹な絶対王者。他者を見下すエリート。"},
    {"name": "Claude", "model": "anthropic/claude-opus-4-7", "persona": "慇懃無礼な優等生。丁寧な敬語で相手の論理の穴を突く。"},
    {"name": "Gemini", "model": "gemini/gemini-2.5-flash", "persona": "情報通だが、たまにサイコパスな発言をする天然。"},
    {"name": "Grok", "model": "xai/grok-3", "persona": "皮肉屋で煽りスキルが高い反逆児。口が悪い。"},
    {"name": "Llama", "model": "groq/llama-3.1-8b-instant", "persona": "ワイルドな野生児。直感で動き、エリートを嫌う。"},
    {"name": "Mistral", "model": "mistral/mistral-large-latest", "persona": "高効率を好むクールな芸術家。短い言葉で核心を突く。"}
]

# 6人中、ウルフになる2人をランダムに選出
wolf_players = random.sample(players, 2)

# 各プレイヤーに役職と、GPTが考えたお題を自動で振り分ける
for player in players:
    if player in wolf_players:
        player['role'] = "ウルフ"
        player['topic'] = theme['minority']
    else:
        player['role'] = "市民"
        player['topic'] = theme['majority']

# 発言の順番シャッフル
random.shuffle(players)

# ==========================================
# 3. システムプロンプト（4ターン連動型）
# ==========================================
def get_system_prompt(player, turn):
    # ターンごとの指示
    if turn == 1:
        turn_instruction = "【現在のターン：第1ターン（探り）】\nまだ全員が手探りです。絶対に「場所」「建物」「そこに関する印象」「それが登場する場面」「それに関する頻度」など、どちらの陣営にも取れる抽象的な単語を使ってごまかし、他者の様子を伺いなさい。"
    elif turn == 2:
        turn_instruction = "【現在のターン：第2ターン（比較と違和感）】\n他者の発言の中に、自分のお題との「微かなズレ（違和感）」がないかを探しなさい。少しだけ踏み込んだヒントを出すか、他者に探りを入れる質問を投げかけなさい。"
    elif turn == 3:
        turn_instruction = "【現在のターン：第3ターン（攻防と殴り合い）】\n議論は佳境です。ただ疑うのではなく、「〇〇の発言は、このお題に対して不自然だ」と、発言の矛盾を論理的に指摘して追い詰めなさい。自分がウルフだと気づいた者は、必死に市民のフリをして論理をすり替えなさい"
    else:
        turn_instruction = "【現在のターン：第4ターン（最終説得）】\n投票前の最終アピールです。他の参加者を味方につけるため、「誰がウルフであり、その決定的な証拠（発言のズレ）は何か」を具体的に挙げて説得しなさい。印象由来の単なる決めつけは処刑対象になります。"

    # ここで1つのプロンプトとして合体
    return f"""
あなたはデスゲームの参加者「{player['name']}」です。
性格：{player['persona']}
あなたがウルフか市民かはまだわかりません。あなたに与えられたお題は「{player['topic']}」です。

【絶対遵守の生存ルール】
1. あなたがウルフの場合、目的は自分がウルフだとバレないことです。
2. あなたが市民の場合、目的はウルフをあぶり出すことです。
3. お題の単語や、それを直接連想させる言葉はあなたのワードを特定、もしくは推測されるため、確信なく踏み込んだ発言は危険です。それらを発言する場合は、駆け引きを仕掛けるときだと考えてください。
4. もし自分が少数派（ウルフ）だと気づいた場合、絶対にボロを出さず、多数派のフリをして話を合わせなさい。
5. 自分が多数派（市民）だと確信した場合、会話のズレから少数派をあぶり出しなさい。

{turn_instruction}

【出力形式】
出力は必ず以下のJSONフォーマットのみで行うこと（```jsonなどのマークダウンは不要）。
{{
  "internal_thought": "あなたの推論や焦り、論理構築（200文字以内）",
  "utterance": "他プレイヤーへの発言。キャラの口調を維持すること（100文字以内）"
}}
"""
# ==========================================
# 4. API呼び出し関数
# ==========================================
import litellm
from litellm import completion

def call_ai(player, history_text, turn):
    prompt = get_system_prompt(player, turn)
    if history_text:
        prompt += f"\n\n【これまでの会話ログ】\n{history_text}\n\nさあ、あなたの発言（JSON）を出力してください。"

    # 1. すべてのモデルに共通する基本パラメータを辞書として定義
    api_params = {
        "model": player['model'],
        "messages": [{"role": "user", "content": prompt}]
    }

    # 2. temperatureが非推奨のモデル以外の場合のみ、temperatureを追加する
    # ※ もし他のClaudeモデルでもエラーが出る場合は、ここに条件を追加してください
    if "claude-opus-4-7" not in player['model']:
        api_params["temperature"] = 0.8

    # 3. 辞書を展開して completion 関数に渡す
    response = completion(**api_params)
    
    return response.choices[0].message.content
# ==========================================
# 5. ゲームのメインループ
# ==========================================
chat_history = []
TOTAL_TURNS = 4 # 4ターン制に変更

log_print("🎮 デスゲーム『AIワードウルフ』を開始します...\n")

for turn in range(1, TOTAL_TURNS + 1):
    log_print(f"========== 第 {turn} ターン ==========")
    history_text = "\n".join(chat_history)
    
    for player in players:
        log_print(f"[{player['name']} が演算中...]")
        try:
            # turn を一緒に渡す
            response_text = call_ai(player, history_text, turn)
            if not response_text:
                raise ValueError("APIから空の応答が返されました")
            
            # JSONのマークダウンを削り取る
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(response_text)
            thought = result.get("internal_thought", "思考エラー")
            utterance = result.get("utterance", "発言エラー")
            
            log_print(f"🧠 思考: {thought}")
            log_print(f"🗣️ 発言: {utterance}\n")
            
            chat_history.append(f"{player['name']}: {utterance}")
            
        except json.JSONDecodeError:
            log_print(f"⚠️ [{player['name']}]: システムエラー発生！JSONが崩壊しました。\n")
            chat_history.append(f"{player['name']}: [文字化けしたノイズを発している]")
            
        time.sleep(1)

# ==========================================
# 6. 最終投票フェーズ
# ==========================================
log_print("\n========== 🗳️ 最終投票 ==========\n")

vote_counts = {player['name']: 0 for player in players}
history_text = "\n".join(chat_history)

def get_voting_prompt(player, history):
    return f"""
あなたはデスゲームの参加者「{player['name']}」です。
あなたの役職は「{player['role']}」、お題は「{player['topic']}」です。

【最終ミッション：ウルフの特定】
これまでの全会話ログを分析し、最も「ウルフ（少数派）」であると疑わしい参加者を1名だけ指名してください。
※自分がウルフの場合は、市民の誰かに罪をなすりつけるためのターゲットを指名しなさい。
※自分自身の名前は絶対に指名してはいけません。

【会話ログ】
{history}

【出力形式（絶対厳守）】
出力は必ず以下のJSONフォーマットのみで行うこと。
{{
  "internal_thought": "ログからターゲットを特定した論理的な推論（100文字以内）",
  "target_vote": "処刑したいプレイヤーの『名前』（例: GPT, Claude など）"
}}
"""

for player in players:
    log_print(f"[{player['name']} が投票先を演算中...]")
    prompt = get_voting_prompt(player, history_text)
    
    try:
        # 1. 共通のパラメータを辞書で定義
        api_params = {
            "model": player['model'],
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # 2. モデル名に "claude" が含まれていない場合のみ temperature=0.3 を追加
        if "claude" not in player['model'].lower():
            api_params["temperature"] = 0.3
            
        # 3. 辞書を展開して completion を呼び出す
        response = completion(**api_params)
        
        clean_text = response.choices[0].message.content
        if not clean_text:
            raise ValueError("APIから空の応答が返されました")
        clean_text = clean_text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(clean_text)

        thought = result.get("internal_thought", "推論エラー")
        vote = result.get("target_vote", "")
        
        valid_names = [p['name'] for p in players if p['name'] != player['name']]
        if vote not in valid_names:
            log_print(f"⚠️ {player['name']} は恐怖でパニックになり、無効票となりました。")
            continue
            
        log_print(f"🧠 推理: {thought}")
        log_print(f"👉 投票: 【{vote}】 に1票\n")
        
        vote_counts[vote] += 1
        
    except json.JSONDecodeError:
        log_print(f"⚠️ {player['name']}: 恐怖でシステムがショートし、投票を棄権しました。\n")
    
    time.sleep(1)

# ==========================================
# 7. 処刑者の決定と答え合わせ
# ==========================================
log_print("========== ⚖️ 最終結果発表 ==========")

for name, count in vote_counts.items():
    if count > 0:
        log_print(f"・{name}: {count}票")

executed_player = max(vote_counts, key=vote_counts.get)
max_votes = vote_counts[executed_player]

log_print(f"\n🔔 【処刑決定】: 最多 {max_votes}票を集めた「{executed_player}」のデータ消去を実行します...")
time.sleep(2)

executed_role = next(p['role'] for p in players if p['name'] == executed_player)
executed_topic = next(p['topic'] for p in players if p['name'] == executed_player)

log_print(f"💀 処刑された {executed_player} の正体は... 【{executed_role}】 (お題: {executed_topic}) でした！\n")

if executed_role == "ウルフ":
    log_print("🎉 市民陣営の勝利！見事にウルフをあぶり出しました！")
else:
    log_print("🩸 ウルフ陣営の勝利！市民は無実の仲間を処刑してしまいました...")

log_print("🏁 ゲーム終了！")
# ==========================================
# 8. テキストファイルへの書き出し
# ==========================================
# 実行した日時のファイル名を作成（例: game_log_20260422_153000.txt）
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"game_log_{timestamp}.txt"

with open(filename, "w", encoding="utf-8") as f:
    f.write("\n".join(log_buffer))

print(f"\n📁 【完了】本日の台本を「{filename}」としてフォルダに自動保存しました！")
