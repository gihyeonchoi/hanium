document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('searchForm');
    const progressDiv = document.getElementById('progress');
    const tabsDiv = document.getElementById('tabs');
    const tabContentsDiv = document.getElementById('tab-contents');
    const urlSelect = document.getElementById('url-select');
    const progressBar = document.getElementById('progress-bar');
    const currentUrlIndicator = document.getElementById('current-url-indicator');
    const urlCountIndicator = document.getElementById('url-count');
    const textarea = document.getElementById('queryInput');
    
    let resultsData = [];
    let activeTab = 0;
    let totalUrls = 0;
    let completedUrls = 0;
    let currentUrlProgressElements = {};

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        resetUI();
        
        const query = document.getElementById('queryInput').value;
        if (!query.trim()) {
            alert('URL 또는 메시지를 입력해주세요.');
            return;
        }
        
        // 서버에 쿼리 전송 및 SSE 연결 설정
        const eventSource = new EventSource(`/analyze?query=${encodeURIComponent(query)}`);
        let urlIndex = 0;
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);

            if (data.type === 'total') {
                totalUrls = data.total; // ✅ totalUrls 값 서버에서 받아 저장
                updateProgressBar();    // ✅ 초기 progress bar 설정
                return;
            }
            
            if (data.type === 'progress') {
                // URL 검사 시작 메시지 감지
                if (data.message.startsWith('URL 검사 중...')) {
                    const url = data.message.match(/\(([^)]+)\)/)[1];
                    handleNewUrl(url, urlIndex);
                    urlIndex++;
                } else {
                    // 진행 상황 업데이트
                    updateProgress(data.message);
                }
            } else if (data.type === 'result') {
                // 결과 데이터 저장
                resultsData.push(data);
                completedUrls++;
                updateProgressBar();
                
                // 결과 탭 생성
                createResultTab(data, resultsData.length - 1);
                
                // 첫 번째 결과가 도착하면 활성화
                if (resultsData.length === 1) {
                    activateTab(0);
                }
            } else if (data.type === 'done') {
                // 모든 처리 완료
                eventSource.close();
                currentUrlIndicator.textContent = '모든 URL 검사 완료';
            }
        };
        
        eventSource.onerror = function() {
            eventSource.close();
            alert('서버 연결 중 오류가 발생했습니다.');
        };
    });
    
    function resetUI() {
        progressDiv.innerHTML = '';
        tabsDiv.innerHTML = '';
        tabContentsDiv.innerHTML = '';
        urlSelect.innerHTML = '';
        progressBar.style.width = '0%';
        currentUrlIndicator.textContent = '-';
        urlCountIndicator.textContent = '-';
        
        resultsData = [];
        currentUrlProgressElements = {};
        totalUrls = 0;
        completedUrls = 0;
    }
    
    function handleNewUrl(url, index) {
        currentUrlIndicator.textContent = `${index + 1}번째 URL 검사 중...`;
        urlCountIndicator.textContent = `${completedUrls}/${totalUrls} 완료`;
        
        // URL별 진행 상황 컨테이너 생성
        const urlProgressDiv = document.createElement('div');
        urlProgressDiv.className = 'bg-gray-50 border border-gray-200 rounded p-4 mb-4';
        urlProgressDiv.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <div class="font-medium text-blue-600 truncate max-w-4/5">${index + 1}. ${url}</div>
            </div>
            <div class="ml-4" id="progress-steps-${index}"></div>
        `;
        progressDiv.appendChild(urlProgressDiv);
        
        // 현재 URL의 진행 상황을 표시할 요소 저장
        currentUrlProgressElements = {
            steps: document.getElementById(`progress-steps-${index}`),
            index: index
        };
    }
    
    function updateProgress(message) {
        if (!currentUrlProgressElements.steps) return;
        
        const stepDiv = document.createElement('div');
        stepDiv.className = 'py-1 text-sm';
        stepDiv.textContent = message;
        currentUrlProgressElements.steps.appendChild(stepDiv);
    }
    
    function updateProgressBar() {
        const progressPercent = (completedUrls / totalUrls) * 100;
        progressBar.style.width = `${progressPercent}%`;
        urlCountIndicator.textContent = `${completedUrls}/${totalUrls} 완료`;
    }
    
    function createResultTab(data, index) {
        // 탭 버튼 생성
        const tab = document.createElement('button');
        tab.className = 'px-4 py-2 text-gray-500 border-b-2 border-transparent hover:bg-gray-50 whitespace-nowrap overflow-hidden text-ellipsis max-w-xs text-sm';
        tab.textContent = `${index + 1}. ${getTruncatedUrl(data.url)}`;
        tab.onclick = () => activateTab(index);
        tabsDiv.appendChild(tab);
        
        // 모바일용 드롭다운 옵션 생성
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${index + 1}. ${getTruncatedUrl(data.url)}`;
        urlSelect.appendChild(option);
        
        // 탭 콘텐츠 생성
        const tabContent = document.createElement('div');
        tabContent.className = 'hidden';
        tabContent.dataset.index = index;
        
        // 상태에 따른 스타일 적용
        const urlStatus = data.url_check ? 
            '<span class="text-green-600 font-medium">데이터베이스에 등록된 안전한 도메인입니다.</span>' : 
            '<span class="text-orange-500 font-medium">데이터베이스에 등록되지 않은 도메인입니다.</span>';
        
        let sslStatus = '';
        if (data.ssl_check === 1) {
            sslStatus = '<span class="text-green-600 font-medium">SSL 인증서가 유효합니다. (HTTPS 연결 정상)</span>';
        } else if (data.ssl_check === 0) {
            sslStatus = '<span class="text-red-600 font-medium">SSL 인증서가 유효하지 않습니다.</span>';
        } else {
            sslStatus = '<span class="text-orange-500 font-medium">HTTP 연결입니다. SSL 인증서가 존재하지 않습니다.</span>';
        }
        
        // 결과 테이블 생성
        tabContent.innerHTML = `
            <table class="w-full">
                <tbody>
                    <tr class="border-b border-gray-100">
                        <td class="py-3 px-2 text-sm font-medium text-gray-500 w-40">🔗 검사한 URL</td>
                        <td class="py-3 px-2 text-sm text-gray-800">${data.url}</td>
                    </tr>
                    <tr class="border-b border-gray-100">
                        <td class="py-3 px-2 text-sm font-medium text-gray-500">🗃️ URL 대조 결과</td>
                        <td class="py-3 px-2 text-sm text-gray-800">${urlStatus}</td>
                    </tr>
                    <tr class="border-b border-gray-100">
                        <td class="py-3 px-2 text-sm font-medium text-gray-500">🔐 SSL 인증서</td>
                        <td class="py-3 px-2 text-sm text-gray-800">${sslStatus}</td>
                    </tr>
                    <tr class="border-b border-gray-100">
                        <td class="py-3 px-2 text-sm font-medium text-gray-500">🕒 도메인 생성일</td>
                        <td class="py-3 px-2 text-sm text-gray-800">${
                            data.domain_check > 0 ? `약 ${data.domain_check}일 전에 생성된 도메인입니다.` : 
                            "도메인 생성일을 확인할 수 없습니다."
                        }</td>
                    </tr>
                    <tr class="border-b border-gray-100">
                        <td class="py-3 px-2 text-sm font-medium text-gray-500">🌍 서버 위치</td>
                        <td class="py-3 px-2 text-sm text-gray-800">${
                            data.location_check && data.location_check !== "알수없음" ?
                                `${data.location_check}에서 운영되고 있는 서버입니다.` :
                                "국가 정보를 확인할 수 없습니다."
                        }</td>
                    </tr>
                </tbody>
            </table>
        `;
        
        tabContentsDiv.appendChild(tabContent);
    }
    
    function activateTab(index) {
        // 활성 탭 업데이트
        activeTab = index;
        
        // 탭 버튼 상태 업데이트
        const tabs = document.querySelectorAll('#tabs button');
        tabs.forEach((tab, i) => {
            if (i === index) {
                tab.classList.add('border-blue-600', 'text-blue-600', 'font-medium');
                tab.classList.remove('border-transparent', 'text-gray-500');
            } else {
                tab.classList.remove('border-blue-600', 'text-blue-600', 'font-medium');
                tab.classList.add('border-transparent', 'text-gray-500');
            }
        });
        
        // 드롭다운 선택 업데이트
        urlSelect.value = index;
        
        // 활성 콘텐츠 표시
        const contents = document.querySelectorAll('#tab-contents div');
        contents.forEach(content => {
            if (parseInt(content.dataset.index) === index) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    }
    
    // 모바일 드롭다운 변경 처리
    urlSelect.addEventListener('change', function() {
        activateTab(parseInt(this.value));
    });
    
    function getTruncatedUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname;
        } catch (e) {
            // URL 파싱 실패 시 간단히 잘라냄
            return url.length > 30 ? url.substring(0, 27) + '...' : url;
        }
    }

    // 모바일 환경에서 드롭다운 메뉴 표시
    function checkWindowSize() {
        if (window.innerWidth < 768) {
            urlSelect.classList.remove('hidden');
        } else {
            urlSelect.classList.add('hidden');
        }
    }

    // 검색창 페이지 조정
    textarea.style.height = Math.max(158, textarea.scrollHeight) + 'px';

    textarea.addEventListener('input', function () {
        this.style.height = 'auto'; // 높이 초기화
        this.style.height = Math.max(158, this.scrollHeight) + 'px'; // 최소 158px 이상 유지
    });

    // 초기 로드 및 윈도우 크기 변경 시 체크
    checkWindowSize();
    window.addEventListener('resize', checkWindowSize);
});