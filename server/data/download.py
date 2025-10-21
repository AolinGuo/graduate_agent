import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import os
import time
import random
import re
import pdfplumber  # PDF转文本库
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import base64

# -------------------------- 核心配置 --------------------------
BASE_URL = "https://www.samr.gov.cn"
API_URL = (
    "https://www.samr.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
)
SAVE_DIR = "市场监管总局-指定分类法规"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": "__jsluid_s=8cee08d03da4972a3e4b1d24ceecfb77; Hm_lvt_54db9897e5a65f7a7b00359d86015d8d=1760965460; HMACCOUNT=AB1F3606D63CDE84; Hm_lpvt_54db9897e5a65f7a7b00359d86015d8d=1760969143",
    "X-Requested-With": "XMLHttpRequest",
}

# 分类配置（替换为实际的xxgkId和nodeId）
CATEGORIES = {
    "相关法律": {"xxgkId": "1202", "nodeId": "11100000MB0143028R"},
    "相关行政法规": {"xxgkId": "1203", "nodeId": "11100000MB0143028R"},
}


# -------------------------- 辅助函数 --------------------------
def create_save_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
        print(f"✅ 已创建保存文件夹：{SAVE_DIR}")


def build_param_json(xxgkId, nodeId, page_no=1, page_size=25):
    search = {
        "createdate": "",
        "depolytime": "",
        "xxgkId": xxgkId,
        "xxgkType": "xxgk_theme",
        "nodeId": nodeId,
        "isFindChild": True,
    }
    param = {
        "pageNo": page_no,
        "pageSize": str(page_size),
        "search": json.dumps(search),
    }
    return json.dumps(param)


def extract_links_by_category(category_name, xxgkId, nodeId):
    all_links = []
    page = 1
    max_pages = 5
    while page <= max_pages:
        param_json = build_param_json(xxgkId, nodeId, page_no=page)
        params = {
            "webId": "29e9522dc89d4e088a953d8cede72f4c",
            "pageId": "20178939d3ff4e2cb6a2301da388b6c9",
            "parseType": "bulidstatic",
            "pageType": "column",
            "tagId": "当前内容",
            "tplSetId": "5c30fb89ae5e48b9aefe3cdf49853830",
            "paramJson": param_json,
        }
        try:
            response = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            law_table = soup.find("table")
            if not law_table:
                print(f"❌ {category_name}第{page}页无表格，停止翻页")
                break
            rows = law_table.find_all("tr")[1:]
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    serial = cells[0].text.strip()
                    title_cell = cells[1]
                    law_title = title_cell.text.strip()
                    publish_date = cells[2].text.strip()
                    doc_no = cells[3].text.strip()
                    a_tag = title_cell.find("a")
                    if a_tag and "href" in a_tag.attrs:
                        # 链接清洗
                        raw_link = a_tag["href"].strip()
                        cleaned_link = re.sub(r'["\']', "", raw_link)
                        law_link = urljoin(BASE_URL, cleaned_link)
                        law_link = law_link.replace("//", "/").replace(
                            "https:/", "https://"
                        )

                        all_links.append(
                            {
                                "serial": serial,
                                "title": law_title,
                                "publish_date": publish_date,
                                "doc_no": doc_no,
                                "link": law_link,
                                "category": category_name,
                            }
                        )
            print(f"✅ {category_name}第{page}页提取到{len(rows)}条法规")
            page += 1
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"❌ {category_name}第{page}页失败：{str(e)}")
            break
    return all_links


def create_chrome_driver():
    """创建Chrome浏览器驱动（自动管理ChromeDriver）"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式（后台运行）
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 使用webdriver_manager自动下载和管理ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def html_to_pdf(url, pdf_path):
    """使用Chrome浏览器将网页内容转换为PDF文件"""
    driver = None
    try:
        # 创建Chrome驱动
        driver = create_chrome_driver()

        # 访问网页
        driver.get(url)

        # 等待页面加载（最多等待10秒）
        time.sleep(3)  # 给页面一些时间来渲染动态内容

        # 使用Chrome的打印功能生成PDF
        print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }

        # 执行打印命令
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)

        # 将base64编码的PDF保存到文件
        with open(pdf_path, "wb") as f:
            f.write(base64.b64decode(result["data"]))

        return True
    except Exception as e:
        print(f"网页转PDF失败：{str(e)}")
        return False
    finally:
        if driver:
            driver.quit()


def pdf_to_text(pdf_path):
    """将PDF文件转换为纯文本"""
    try:
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        return "\n\n".join(text_content)
    except Exception as e:
        print(f"PDF转文本失败：{str(e)}")
        return None


def crawl_and_convert_to_text(law_info):
    """将网页内容转换为PDF，然后再转换为纯文本"""
    serial = law_info["serial"]
    title = law_info["title"]
    link = law_info["link"]
    category = law_info["category"]

    try:
        time.sleep(random.uniform(1.5, 3))

        # 创建保存目录
        category_dir = os.path.join(SAVE_DIR, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        safe_title = "".join([c for c in title if c not in '/:*?"<>|'])
        pdf_filename = f"第{serial}条-{safe_title}.pdf"
        pdf_path = os.path.join(category_dir, pdf_filename)

        # 1. 将网页转换为PDF
        print(f"📄 第{serial}条《{title}》正在将网页转换为PDF...")
        if html_to_pdf(link, pdf_path):
            print(f"✅ 网页已转换为PDF：{pdf_filename}")

            # 2. 将PDF转换为文本
            print("📝 正在将PDF转换为文本...")
            text_content = pdf_to_text(pdf_path)

            if text_content:
                # 3. 保存文本文件
                txt_filename = f"第{serial}条-{safe_title}.txt"
                txt_path = os.path.join(category_dir, txt_filename)

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"【标题】{title}\n")
                    f.write(f"【发布日期】{law_info['publish_date']}\n")
                    f.write(
                        f"【文号】{law_info['doc_no'] if law_info['doc_no'].strip() else '无'}\n"
                    )
                    f.write(f"【链接】{link}\n")
                    f.write(f"【PDF文件】{pdf_filename}\n\n")
                    f.write("========== 网页内容（从PDF转换） ==========\n\n")
                    f.write(text_content)

                print(
                    f"✅ {category}第{serial}条《{title}》已保存（文本长度：{len(text_content)}字符）"
                )
                print(f"   📁 PDF文件：{pdf_filename}")
                print(f"   📁 文本文件：{txt_filename}\n")
            else:
                print(f"❌ 第{serial}条《{title}》PDF转文本失败\n")
        else:
            print(f"❌ 第{serial}条《{title}》网页转PDF失败\n")

    except Exception as e:
        print(f"❌ {category}第{serial}条处理失败：{str(e)}\n")


# -------------------------- 主函数 --------------------------
def main():
    print("===== 开始爬取指定分类法规（网页→PDF→文本） =====")
    create_save_dir()

    for category_name, category_info in CATEGORIES.items():
        xxgkId = category_info["xxgkId"]
        nodeId = category_info["nodeId"]
        print(f"\n----- 开始爬取「{category_name}」-----")

        law_links = extract_links_by_category(category_name, xxgkId, nodeId)
        print(f"共提取到{len(law_links)}条「{category_name}」法规")

        for law in law_links:
            crawl_and_convert_to_text(law)

    print("===== 所有分类爬取完成 =====")


if __name__ == "__main__":
    main()
