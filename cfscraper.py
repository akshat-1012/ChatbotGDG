import os
import re
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup as soup
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
}
 
def create_directories():
    os.makedirs("data/metadata", exist_ok=True)
    os.makedirs("data/problem_statements", exist_ok=True)
    os.makedirs("data/editorials", exist_ok=True)

def extract_problem_id(input_string):
    match = re.match(r'^([A-Za-z0-9]+)\.', input_string)
    return match.group(1) if match else None

def extract_name(input_string):
    match = re.search(r'^[A-Za-z0-9]+\.\s*(.*)', input_string)
    return match.group(1) if match else "No match found"

def extract_contest_id(input_string):
    match = re.search(r'/contest/(\d+)', input_string)
    return match.group(1) if match else "No contest ID found in the URL"

def fetch_page_content(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return soup(response.content, "lxml")

def find_question_details(question_link):
    page_soup = fetch_page_content(question_link)

    # Remove any math spans for cleaner text
    for span in page_soup.find_all("span", {"class": "math"}):
        span.decompose()

    prob_name = page_soup.find("div", class_="title").text.strip()
    problem = page_soup.find("div", class_="problem-statement")
    question = problem.find("div", id=False, class_=False)
    problem_statement = "\n".join([p.text for p in question.find_all('p')])

    with open(f"data/problem_statements/{prob_name}_statement.txt", "w", encoding="utf-8") as f:
        f.write(problem_statement)

    time_limit = page_soup.find("div", class_="time-limit").text.replace("time limit per test", "").strip()
    memory_limit = page_soup.find("div", class_="memory-limit").text.replace("memory limit per test", "").strip()

    tags = [tag.text.strip() for tag in page_soup.find_all("span", class_="tag-box")]
    last_tag = tags[-1] if tags else ""
    difficulty = last_tag if last_tag.startswith('*') else "unknown"
    if difficulty != "unknown":
        tags.pop()

    input_spec = page_soup.find("div", class_="input-specification").text.strip()
    output_spec = page_soup.find("div", class_="output-specification").text.strip()
    tests = page_soup.find("div", class_="sample-test").text.strip()

    problem_metadata = {
        "problem_id": extract_problem_id(prob_name),
        "contest_id": extract_contest_id(question_link),
        "name": prob_name,
        "url": question_link,
        "difficulty": difficulty,
        "tags": tags,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "input_specification": input_spec,
        "output_specification": output_spec,
        "sample_tests": tests
    }

    with open(f"data/metadata/{prob_name}_metadata.json", "w", encoding="utf-8") as file:
        json.dump(problem_metadata, file, indent=4)

    return prob_name

def extract_editorial_link(contest_link):
    # Fetch the content of the contest page
    page_soup = fetch_page_content(contest_link)
    
    # Look for the "Contest materials" section (sidebar)
    sidebar = page_soup.find("div", class_="roundbox sidebox sidebar-menu")
    
    # Debugging: Print out the sidebar to confirm we're accessing the correct section
    if sidebar:
        print("Sidebar found.")
        links = sidebar.find_all("a", href=True)
        
        # Debugging: print all links to see the actual structure
        for link in links:
            print(f"Found link: {link.text.strip()} -> {link['href']}")
        
        for link in links:
            # Check if "Tutorial" is in the link's text (case insensitive)
            if "tutorial" in link.text.lower():
                editorial_url = urljoin("https://codeforces.com", link['href'])
                print(f"Editorial link found: {editorial_url}")  # Debugging the editorial link
                return editorial_url
    
    print("No editorial link found.")
    return None


def extract_editorial_content(link_editorial, problem_names):
    if not link_editorial:
        print("No editorial link found.")
        return

    # Fetch the content of the editorial page
    page_soup = fetch_page_content(link_editorial)

    # Remove any math spans
    for span in page_soup.find_all("span", {"class": "math"}):
        span.decompose()

    # Locate the main editorial content
    content = page_soup.find("div", class_="ttypography")
    if not content:
        print("Editorial content not found on the page.")
        return

    result = []
    current_problem_index = 0

    for ele in content.children:
        # Match the problem name and write the previous editorial if matched
        if (
            current_problem_index < len(problem_names) and
            extract_name(problem_names[current_problem_index]) in ele.text
        ):
            if current_problem_index > 0:
                with open(f"data/editorials/{problem_names[current_problem_index - 1]}_editorial.txt", "w", encoding="utf-8") as f:
                    f.write("\n".join(result))
            result = []
            current_problem_index += 1
        elif ele.name:  # Collect text from valid tags
            result.append(ele.text.strip())

    # Save the final editorial content for the last problem
    if result:
        with open(f"data/editorials/{problem_names[-1]}_editorial.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(result))


def get_all_prob(contest_link):
    page_soup = fetch_page_content(contest_link)
    problems = page_soup.find("table", class_="problems")
    return sorted(
        {urljoin(contest_link, a['href']) for a in problems.find_all('a', href=True) if '/problem/' in a['href']}
    )

if __name__ == '__main__':
    create_directories()
    contest_link = "https://codeforces.com/contest/2050"
    prob_names = [find_question_details(url) for url in get_all_prob(contest_link)]
    editorial_link = extract_editorial_link(contest_link)
    extract_editorial_content(editorial_link, prob_names)
