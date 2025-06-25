from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re

# ----------- ログイン情報を入力-----------
USERNAME = "08615201766581"
PASSWORD = "After592025"
# ---------------------------------------------

# ブラウザ設定 
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # ウィンドウを最大化
driver = webdriver.Chrome(options=options)

def login_instagram():
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.ENTER)

    print("登录中...")
    time.sleep(7)  # ログイン完了までしばらく待つ

def go_to_tag_page(tag="ちいかわ"):
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    driver.get(url)
    print(f"ハッシュタグページへ移動中 #{tag}...")
    time.sleep(5)

def collect_post_links(limit=10):
    print("投稿のリンク収集中...")
    links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(links) < limit:
        elements = driver.find_elements(By.TAG_NAME, "a")
        for el in elements:
            href = el.get_attribute("href")
            if href and "/p/" in href:
                links.add(href)
                if len(links) >= limit:
                    break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        print(f" {len(links)} 件のリンクを取得した")
    
    print("リンクの取得が完了")
    return list(links)

def scrape_posts(post_links):
    print("投稿内容のスクレイピングを開始...")
    data = []
    for idx, link in enumerate(post_links):
        print(f" {idx + 1}/{len(post_links)} 件目を取得中：{link}")
        driver.get(link)
        
        # 少し長めに待機して人間らしい操作を再現する
        time.sleep(5)
        
        # ページをスクロールしてコンテンツを読み込み
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)
        
        # 等待页面完全加载ページが完全に読み込まれるのを待っている
        wait = WebDriverWait(driver, 30)
        
        # ページが正しく表示されているか確認中
        page_loaded = False
        try:
            # よく使われる要素の表示を待っている
            wait.until(EC.any_of(
                EC.presence_of_element_located((By.TAG_NAME, "article")),
                EC.presence_of_element_located((By.TAG_NAME, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='main']"))
            ))
            page_loaded = True
            print(" ページの読み込み成功")
        except:
            print(" ページの読み込みに失敗した可能性があるため、リロードする...")
            driver.refresh()
            time.sleep(10)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
                page_loaded = True
                print(" リロード後、ページの読み込みに成功した ")
            except:
                print(" ページが正しく読み込めなかったため、この投稿はスキップする")
                continue
        
        if not page_loaded:
            continue
            
        # 打デバッグのため、HTML構造を出力する
        print("  ページ構造を解析中...")
        try:
            # タイトルを取得して正しいページか確認する
            page_title = driver.title
            print(f"  页面标题: {page_title}")
            
            # 考えられる全てのコンテナ要素を探す
            containers = ['main', 'article', 'section', 'div[role="main"]']
            main_content = None
            
            for container in containers:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, container)
                    if elements:
                        main_content = elements[0]
                        print(f"  メインコンテナを見つけた: {container}")
                        break
                except:
                    continue
            
            if not main_content:
                print(" メインコンテナが見つからないため、body要素から取得を試す...")
                main_content = driver.find_element(By.TAG_NAME, "body")
            
        except Exception as e:
            print(f" ページ解析中にエラーが発生した: {e}")
            continue
        
        # ユーザー名の取得
        username = ""
        try:
            # URLからユーザー名を取得
            url_parts = link.split('/')
            if len(url_parts) > 3:
                # ユーザー名を取得するために複数の方法を試す
                username_methods = [
                    # 方法1: リンクからユーザー名を探す
                    lambda: [a.get_attribute('href') for a in driver.find_elements(By.TAG_NAME, 'a') 
                            if a.get_attribute('href') and '/' in a.get_attribute('href') and '/p/' not in a.get_attribute('href')],
                    # 方法2: @から始まるテキストを探す
                    lambda: [elem.text for elem in driver.find_elements(By.XPATH, "//*[starts-with(text(), '@')]")],
                    # 方法3: title属性から取得する
                    lambda: [elem.get_attribute('title') for elem in driver.find_elements(By.XPATH, "//*[@title]")]
                ]
                
                for method in username_methods:
                    try:
                        results = method()
                        for result in results[:5]:  # 上位5件のみをチェックする
                            if result and isinstance(result, str):
                                if result.startswith('@'):
                                    username = result[1:]  # @記号を取り除く
                                    break
                                elif '/' in result and not '/p/' in result:
                                    parts = result.strip('/').split('/')
                                    if len(parts) >= 1 and parts[-1]:
                                        username = parts[-1]
                                        break
                        if username:
                            break
                    except:
                        continue
                        
        except Exception as e:
            print(f"  ユーザー名の取得中にエラーが発生した: {e}")
        
        # 投稿内容の取得
        content = ""
        full_text = ""
        try:
            # すべてのテキストを取得して、フィルタリングする
            all_texts = []
            
            # テキストが含まれていそうな要素をすべてチェックする
            text_elements = driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text())) > 5]")
            
            for elem in text_elements:
                try:
                    text = elem.text.strip()
                    if len(text) > 5 and text not in all_texts:
                        all_texts.append(text)
                except:
                    continue
            
            print(f" {len(all_texts)} 件のテキストを見つけた")
            
            # 投稿本文らしいテキストを選別中（適度な長さ・意味のある内容）
            for text in all_texts:
                if 20 < len(text) < 500 and not text.isdigit():
                    # 日本語やハッシュタグなどが含まれているかチェックする
                    if any(ord(char) > 127 for char in text) or '#' in text:
                        full_text = text
                        break
            
            # 適切なものが見つからなければ、最長のテキストを使用する
            if not full_text and all_texts:
                full_text = max(all_texts, key=len)
                
        except Exception as e:
            print(f"  投稿内容の取得中にエラーが発生した: {e}")
        
        # 本文とハッシュタグを分離する
        if "#" in full_text:
            parts = full_text.split('#', 1)
            content = parts[0].strip()
            tag_part = '#' + parts[1] if len(parts) > 1 else ''
            tags = re.findall(r'#\w+', tag_part)
        else:
            content = full_text
            tags = []
        
        # 投稿日時を取得する
        timestamp = ""
        try:
            time_elements = driver.find_elements(By.TAG_NAME, "time")
            for time_elem in time_elements:
                datetime_attr = time_elem.get_attribute("datetime")
                if datetime_attr:
                    timestamp = datetime_attr
                    break
        except:
            pass
        
        # いいね数を取得する
        likes = ""
        try:
            print("  いいね数の検索を開始する...")
            
            # 等待页面完全加载
            time.sleep(3)
            
            # 方法1: ハートアイコン付近の数字を探す
            try:
                # 考えられるすべてのハートアイコン要素を探す
                heart_selectors = [
                    "svg[aria-label*='like']",
                    "svg[aria-label*='Like']", 
                    "svg[aria-label*='赞']",
                    "*[data-testid*='like']",
                    "button[aria-label*='like']",
                    "button[aria-label*='Like']"
                ]
                
                for selector in heart_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for heart_elem in elements:
                        # ハートアイコンの親要素または兄弟要素から数字を探す
                        parent = heart_elem.find_element(By.XPATH, "./..")
                        siblings = parent.find_elements(By.XPATH, "./*")
                        
                        for sibling in siblings:
                            text = sibling.text.strip()
                            # 数字のフォーマットにマッチするかを確認する（カンマ・万・kなど含む）
                            if re.match(r'^\d+[,.]?\d*[万千kKmM]?$', text):
                                likes = text
                                print(f"  ハートアイコン周辺からいいね数を取得した: {likes}")
                                break
                        if likes:
                            break
                    if likes:
                        break
            except Exception as e:
                print(f"  方法1は失败した: {e}")
            
            # 方法2: ボタンのaria-labelを検索する
            if not likes:
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        aria_label = button.get_attribute("aria-label")
                        if aria_label and ("like" in aria_label.lower() or "赞" in aria_label):
                            # aria-labelから数字を抽出する
                            numbers = re.findall(r'([\d,]+)', aria_label)
                            if numbers:
                                likes = numbers[0]
                                print(f"  ボタンのaria-labelからいいね数を取得した: {likes}")
                                break
                except Exception as e:
                    print(f"  方法2は失败した: {e}")
            
            # 方法3: 特定のキーワードを含むspan要素を検索する
            if not likes:
                try:
                    spans = driver.find_elements(By.TAG_NAME, "span")
                    for span in spans:
                        text = span.text.strip()
                        # 「赞」「likes」などのキーワードを含むテキストを探す
                        if any(keyword in text.lower() for keyword in ["个赞", "likes", "like"]):
                            numbers = re.findall(r'([\d,]+)', text)
                            if numbers:
                                likes = numbers[0]
                                print(f" span内のテキストからいいね数を取得した: {likes}")
                                break
                except Exception as e:
                    print(f"  方法3は失败した: {e}")
            
            # 方法4: 通过JavaScript获取
            if not likes:
                try:
                    # JavaScriptを使用してページ内の数字を取得する
                    js_script = """
                    var numbers = [];
                    var allElements = document.querySelectorAll('*');
                    for (var i = 0; i < allElements.length; i++) {
                        var text = allElements[i].textContent.trim();
                        if (/^\\d+[,.]?\\d*[万千kKmM]?$/.test(text) && text.length < 10) {
                            var rect = allElements[i].getBoundingClientRect();
                            // ページの上半分にある数字のみを対象にする
                            if (rect.top < window.innerHeight * 0.6) {
                                numbers.push(text);
                            }
                        }
                    }
                    return numbers.slice(0, 5); // 上位5つの数字を返す
                    """
                    numbers = driver.execute_script(js_script)
                    if numbers:
                        # 最初に見つかった数字をいいね数として使用する
                        likes = numbers[0]
                        print(f"  JavaScriptを使っていいね数を取得した: {likes}")
                except Exception as e:
                    print(f"  方法4は失败した: {e}")
            
            # 方法5: 全体の数字を探し、位置に基づいて判断する
            if not likes:
                try:
                    all_elements = driver.find_elements(By.XPATH, "//*[text()]")
                    potential_likes = []
                    
                    for elem in all_elements:
                        text = elem.text.strip()
                        if re.match(r'^\d+[,.]?\d*[万千kKmM]?$', text) and len(text) < 8:
                            try:
                                # 要素の位置を取得する
                                location = elem.location
                                size = elem.size
                                
                                # いいね数は通常、ページの左または中央、かつ上部に表示されることが多い
                                window_height = driver.get_window_size()['height']
                                window_width = driver.get_window_size()['width']
                                
                                if (location['y'] < window_height * 0.6 and 
                                    location['x'] < window_width * 0.8):
                                    potential_likes.append((text, location['y']))
                            except:
                                pass
                    
                    # y座標で並べ替えて、一番上の数字を選ぶ
                    if potential_likes:
                        potential_likes.sort(key=lambda x: x[1])
                        likes = potential_likes[0][0]
                        print(f"  位置情報に基づいていいね数を特定した: {likes}")
                        
                except Exception as e:
                    print(f"  方法5は失败した: {e}")
            
            # すべての方法で失敗した場合、「不明」とする
            if not likes:
                likes = "不明"
                print("  どの方法でもいいね数が取得できませんでした")
                
        except Exception as e:
            print(f"  いいね数の取得中にエラーが発生した: {e}")
            likes = "取得失敗"
        
        # デバッグ情報を出力する
        print(f"  ユーザー名: '{username}'")
        print(f"  本文の長さ: {len(content)}")
        print(f"  ハッシュタグの数: {len(tags)}")
        print(f"  いいね数: '{likes}'")
        print(f"  投稿日時: '{timestamp}'")
        if full_text:
            print(f"  原文プレビュー: '{full_text[:100]}...'")
        
        data.append({
            "url": link,
            "username": username,
            "timestamp": timestamp,
            "content": content,
            "tags": tags,
            "likes": likes,
            "full_text": full_text
        })
        
        # 各投稿の間に遅延を入れて、Bot検出を回避する
        time.sleep(3)

    print("データの取得が完了した")
    return data



def save_to_json(data, filename="chiikawa_tag_data.json"):
    print("データを保存中...")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f" {len(data)} 件のデータを {filename}に保存した")

# 処理を開始する
login_instagram()
go_to_tag_page("ちいかわ")
post_links = collect_post_links(limit=10)
data = scrape_posts(post_links)
save_to_json(data)
driver.quit()
