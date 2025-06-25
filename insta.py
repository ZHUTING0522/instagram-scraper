from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re

# ----------- 你的账号信息（自己填上）-----------
USERNAME = "08615201766581"
PASSWORD = "After592025"
# ---------------------------------------------

# 设置浏览器选项 
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # 最大化窗口，方便加载元素
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
    time.sleep(7)  # 等待登录完成

def go_to_tag_page(tag="ちいかわ"):
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    driver.get(url)
    print(f"跳转到标签页 #{tag}...")
    time.sleep(5)

def collect_post_links(limit=3):
    print("开始收集帖子的链接...")
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
        print(f"已收集 {len(links)} 条链接")
    
    print("链接收集完毕！")
    return list(links)

def scrape_posts(post_links):
    print("开始抓取帖子内容...")
    data = []
    for idx, link in enumerate(post_links):
        print(f"抓取第 {idx + 1}/{len(post_links)} 篇：{link}")
        driver.get(link)
        
        # 增加更长的等待时间并模拟人类行为
        time.sleep(5)
        
        # 模拟向下滚动，触发内容加载
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)
        
        # 等待页面完全加载
        wait = WebDriverWait(driver, 30)
        
        # 首先检查页面是否正常加载
        page_loaded = False
        try:
            # 等待任意一个常见元素出现
            wait.until(EC.any_of(
                EC.presence_of_element_located((By.TAG_NAME, "article")),
                EC.presence_of_element_located((By.TAG_NAME, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='main']"))
            ))
            page_loaded = True
            print("  页面加载成功")
        except:
            print("  页面加载可能有问题，尝试刷新...")
            driver.refresh()
            time.sleep(10)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
                page_loaded = True
                print("  刷新后页面加载成功")
            except:
                print("  页面仍然无法正常加载，跳过此帖子")
                continue
        
        if not page_loaded:
            continue
            
        # 打印页面HTML结构用于调试
        print("  正在分析页面结构...")
        try:
            # 获取页面标题，确认我们在正确的页面
            page_title = driver.title
            print(f"  页面标题: {page_title}")
            
            # 查找所有可能的容器元素
            containers = ['main', 'article', 'section', 'div[role="main"]']
            main_content = None
            
            for container in containers:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, container)
                    if elements:
                        main_content = elements[0]
                        print(f"  找到主容器: {container}")
                        break
                except:
                    continue
            
            if not main_content:
                print("  未找到主容器，尝试获取body内容...")
                main_content = driver.find_element(By.TAG_NAME, "body")
            
        except Exception as e:
            print(f"  页面分析出错: {e}")
            continue
        
        # 获取用户名 - 简化方法
        username = ""
        try:
            # 从URL中提取用户名（备选方案）
            url_parts = link.split('/')
            if len(url_parts) > 3:
                # 尝试多种方法获取用户名
                username_methods = [
                    # 方法1: 查找所有链接，找用户名模式
                    lambda: [a.get_attribute('href') for a in driver.find_elements(By.TAG_NAME, 'a') 
                            if a.get_attribute('href') and '/' in a.get_attribute('href') and '/p/' not in a.get_attribute('href')],
                    # 方法2: 查找所有文本，找@开头的
                    lambda: [elem.text for elem in driver.find_elements(By.XPATH, "//*[starts-with(text(), '@')]")],
                    # 方法3: 查找title属性
                    lambda: [elem.get_attribute('title') for elem in driver.find_elements(By.XPATH, "//*[@title]")]
                ]
                
                for method in username_methods:
                    try:
                        results = method()
                        for result in results[:5]:  # 只检查前5个结果
                            if result and isinstance(result, str):
                                if result.startswith('@'):
                                    username = result[1:]  # 移除@符号
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
            print(f"  获取用户名出错: {e}")
        
        # 获取内容 - 简化方法
        content = ""
        full_text = ""
        try:
            # 获取所有文本内容，然后筛选
            all_texts = []
            
            # 查找所有可能包含文本的元素
            text_elements = driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text())) > 5]")
            
            for elem in text_elements:
                try:
                    text = elem.text.strip()
                    if len(text) > 5 and text not in all_texts:
                        all_texts.append(text)
                except:
                    continue
            
            print(f"  找到 {len(all_texts)} 段文本")
            
            # 筛选出最可能是内容的文本（长度适中，包含有意义内容）
            for text in all_texts:
                if 20 < len(text) < 500 and not text.isdigit():
                    # 检查是否包含日文字符或常见内容特征
                    if any(ord(char) > 127 for char in text) or '#' in text:
                        full_text = text
                        break
            
            # 如果没找到，取最长的文本
            if not full_text and all_texts:
                full_text = max(all_texts, key=len)
                
        except Exception as e:
            print(f"  获取内容出错: {e}")
        
        # 分离内容和标签
        if "#" in full_text:
            parts = full_text.split('#', 1)
            content = parts[0].strip()
            tag_part = '#' + parts[1] if len(parts) > 1 else ''
            tags = re.findall(r'#\w+', tag_part)
        else:
            content = full_text
            tags = []
        
        # 获取时间戳
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
        
        # 获取点赞数 - 重新设计
        likes = ""
        try:
            print("  开始查找点赞数...")
            
            # 等待页面完全加载
            time.sleep(3)
            
            # 方法1: 查找心形图标附近的数字
            try:
                # 查找所有可能的心形图标元素
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
                        # 查找心形图标的父元素或兄弟元素中的数字
                        parent = heart_elem.find_element(By.XPATH, "./..")
                        siblings = parent.find_elements(By.XPATH, "./*")
                        
                        for sibling in siblings:
                            text = sibling.text.strip()
                            # 匹配数字格式（包括带逗号、万、k等）
                            if re.match(r'^\d+[,.]?\d*[万千kKmM]?$', text):
                                likes = text
                                print(f"  从心形图标附近找到点赞数: {likes}")
                                break
                        if likes:
                            break
                    if likes:
                        break
            except Exception as e:
                print(f"  方法1失败: {e}")
            
            # 方法2: 查找按钮的aria-label
            if not likes:
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        aria_label = button.get_attribute("aria-label")
                        if aria_label and ("like" in aria_label.lower() or "赞" in aria_label):
                            # 从aria-label中提取数字
                            numbers = re.findall(r'([\d,]+)', aria_label)
                            if numbers:
                                likes = numbers[0]
                                print(f"  从按钮aria-label找到点赞数: {likes}")
                                break
                except Exception as e:
                    print(f"  方法2失败: {e}")
            
            # 方法3: 查找包含特定关键词的span元素
            if not likes:
                try:
                    spans = driver.find_elements(By.TAG_NAME, "span")
                    for span in spans:
                        text = span.text.strip()
                        # 查找包含"赞"、"likes"等关键词的文本
                        if any(keyword in text.lower() for keyword in ["个赞", "likes", "like"]):
                            numbers = re.findall(r'([\d,]+)', text)
                            if numbers:
                                likes = numbers[0]
                                print(f"  从span文本找到点赞数: {likes}")
                                break
                except Exception as e:
                    print(f"  方法3失败: {e}")
            
            # 方法4: 通过JavaScript获取
            if not likes:
                try:
                    # 使用JavaScript查找页面中的数字
                    js_script = """
                    var numbers = [];
                    var allElements = document.querySelectorAll('*');
                    for (var i = 0; i < allElements.length; i++) {
                        var text = allElements[i].textContent.trim();
                        if (/^\\d+[,.]?\\d*[万千kKmM]?$/.test(text) && text.length < 10) {
                            var rect = allElements[i].getBoundingClientRect();
                            // 只取页面上半部分的数字
                            if (rect.top < window.innerHeight * 0.6) {
                                numbers.push(text);
                            }
                        }
                    }
                    return numbers.slice(0, 5); // 返回前5个数字
                    """
                    numbers = driver.execute_script(js_script)
                    if numbers:
                        # 取第一个数字作为点赞数
                        likes = numbers[0]
                        print(f"  通过JavaScript找到点赞数: {likes}")
                except Exception as e:
                    print(f"  方法4失败: {e}")
            
            # 方法5: 查找所有数字，基于位置判断
            if not likes:
                try:
                    all_elements = driver.find_elements(By.XPATH, "//*[text()]")
                    potential_likes = []
                    
                    for elem in all_elements:
                        text = elem.text.strip()
                        if re.match(r'^\d+[,.]?\d*[万千kKmM]?$', text) and len(text) < 8:
                            try:
                                # 获取元素位置
                                location = elem.location
                                size = elem.size
                                
                                # 点赞数通常在页面左侧或中间，且在上半部分
                                window_height = driver.get_window_size()['height']
                                window_width = driver.get_window_size()['width']
                                
                                if (location['y'] < window_height * 0.6 and 
                                    location['x'] < window_width * 0.8):
                                    potential_likes.append((text, location['y']))
                            except:
                                pass
                    
                    # 按y坐标排序，取最上面的数字
                    if potential_likes:
                        potential_likes.sort(key=lambda x: x[1])
                        likes = potential_likes[0][0]
                        print(f"  基于位置找到点赞数: {likes}")
                        
                except Exception as e:
                    print(f"  方法5失败: {e}")
            
            # 如果所有方法都失败，设置为未知
            if not likes:
                likes = "未知"
                print("  所有方法都无法获取点赞数")
                
        except Exception as e:
            print(f"  获取点赞数总体出错: {e}")
            likes = "获取失败"
        
        # 输出调试信息
        print(f"  用户名: '{username}'")
        print(f"  内容长度: {len(content)}")
        print(f"  标签数量: {len(tags)}")
        print(f"  点赞数: '{likes}'")
        print(f"  时间戳: '{timestamp}'")
        if full_text:
            print(f"  原始文本预览: '{full_text[:100]}...'")
        
        data.append({
            "url": link,
            "username": username,
            "timestamp": timestamp,
            "content": content,
            "tags": tags,
            "likes": likes,
            "full_text": full_text
        })
        
        # 每个帖子之间增加延迟，避免被检测
        time.sleep(3)

    print("数据抓取完毕")
    return data



def save_to_json(data, filename="chiikawa_tag_data.json"):
    print("正在保存数据...")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(data)} 条数据到 {filename}")

# 执行流程
login_instagram()
go_to_tag_page("ちいかわ")
post_links = collect_post_links(limit=3)
data = scrape_posts(post_links)
save_to_json(data)
driver.quit()
