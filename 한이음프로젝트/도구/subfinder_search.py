
# =============================================================================
# 함수 domain_search()
# CSV 파일 경로에 있는 URL을 자동으로 subfinder에 넣고 실행
# =============================================================================
def domain_search():
    import csv
    import subprocess
    import os
    from concurrent.futures import ThreadPoolExecutor
    
    # 경로 이동
    os.chdir(r"C:\Users\user07\Desktop\hanium\한이음프로젝트\domains_data")
    
    # CSV 파일 경로
    csv_path = r"C:\Users\user07\Desktop\hanium\한이음프로젝트\도구\subfinder_test.csv"
    
    # 각 작업을 실행할 함수
    def run_subfinder(url, name):
        output_file = f"{name}.txt"
        command = ["subfinder", "-d", url, "-o", output_file]
        print("실행 중:", " ".join(command))
        subprocess.run(command)
    
    # CSV 읽기 및 병렬 실행
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        with ThreadPoolExecutor(max_workers=10) as executor:  # 최대 5개 병렬 실행
            for row in reader:
                url = row['URL'].strip()
                name = row['사이트이름'].strip()
                executor.submit(run_subfinder, url, name)

# domain_search()

#############################

def txt_file_merge():
    import os
    # 합칠 파일들이 있는 폴더 경로
    folder_path = r"../domains_data"
    
    # 결과 파일 이름 (원하는 대로 수정 가능)
    output_file = os.path.join(folder_path, "all_subdomains.txt")
    
    # 중복 제거를 위해 set 사용
    all_lines = set()
    
    # 폴더 내 .txt 파일 순회
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt") and filename != "all_subdomains.txt":
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    cleaned = line.strip()
                    if cleaned:  # 빈 줄 제거
                        all_lines.add(cleaned)
    
    # 결과 파일에 저장
    with open(output_file, "w", encoding="utf-8") as out_file:
        for line in sorted(all_lines):  # 정렬 원하면 sorted 사용, 안 해도 무방
            out_file.write(line + "\n")
    
    print(f"✅ {len(all_lines)}개의 도메인을 '{output_file}'에 저장했습니다.")
    

txt_file_merge()
