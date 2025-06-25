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
        
        # 获取点赞数
        likes = ""
        try:
            # 查找包含数字的文本
            number_texts = []
            elements = driver.find_elements(By.XPATH, "//*[text()[contains(., '万') or contains(., 'k') or contains(., 'K') or contains(., ',')]]")
            for elem in elements:
                text = elem.text.strip()
                if any(char.isdigit() for char in text) and len(text) < 20:
                    number_texts.append(text)
            
            if number_texts:
                likes = number_texts[0]  # 取第一个符合条件的
                
        except:
            pass
        
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
