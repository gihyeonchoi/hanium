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
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'flex justify-between items-center mb-2';
        
        const urlLabel = document.createElement('div');
        urlLabel.className = 'font-medium text-blue-600 truncate max-w-4/5';
        urlLabel.textContent = `${index + 1}. ${url}`;
        
        headerDiv.appendChild(urlLabel);
        urlProgressDiv.appendChild(headerDiv);
        
        const stepsDiv = document.createElement('div');
        stepsDiv.className = 'ml-4';
        stepsDiv.id = `progress-steps-${index}`;
        urlProgressDiv.appendChild(stepsDiv);
        
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
        
        // 테이블 생성
        const table = document.createElement('table');
        table.className = 'w-full';
        const tbody = document.createElement('tbody');
        
        // URL 행
        const urlRow = createTableRow('🔗 검사한 URL', data.url);
        tbody.appendChild(urlRow);
        
        // URL 대조 결과 행
        const urlStatus = data.url_check ? 
            createStatusSpan('데이터베이스에 등록된 안전한 도메인입니다.', 'text-green-600') : 
            createStatusSpan('데이터베이스에 등록되지 않은 도메인입니다.', 'text-orange-500');
        const urlCheckRow = createTableRow('🗃️ URL 대조 결과', urlStatus);
        tbody.appendChild(urlCheckRow);
        
        // SSL 인증서 행
        let sslStatus;
        if (data.ssl_check === 1) {
            sslStatus = createStatusSpan('SSL 인증서가 유효합니다. (HTTPS 연결 정상)', 'text-green-600');
        } else if (data.ssl_check === 0) {
            sslStatus = createStatusSpan('SSL 인증서가 유효하지 않습니다.', 'text-red-600');
        } else {
            sslStatus = createStatusSpan('HTTP 연결입니다. SSL 인증서가 존재하지 않습니다.', 'text-orange-500');
        }
        const sslRow = createTableRow('🔐 SSL 인증서', sslStatus);
        tbody.appendChild(sslRow);
        
        // 도메인 생성일 행
        let domainStatus;
        if (data.domain_check > 0) {
            domainStatus = document.createTextNode(`약 ${data.domain_check}일 전에 생성된 도메인입니다.`);
        } else {
            domainStatus = document.createTextNode("도메인 생성일을 확인할 수 없습니다.");
        }
        const domainRow = createTableRow('🕒 도메인 생성일', domainStatus);
        tbody.appendChild(domainRow);
        
        // 서버 위치 행
        let locationStatus;
        if (data.location_check && data.location_check !== "알수없음") {
            locationStatus = document.createTextNode(`${data.location_check}에서 운영되고 있는 서버입니다.`);
        } else {
            locationStatus = document.createTextNode("국가 정보를 확인할 수 없습니다.");
        }
        const locationRow = createTableRow('🌍 서버 위치', locationStatus);
        tbody.appendChild(locationRow);
        
        table.appendChild(tbody);
        tabContent.appendChild(table);
        
        // 위험도 평가 섹션 추가
        if (data.risk_level !== undefined) {
            const riskSection = createRiskAssessmentSection(data.risk_level, data.risk_messages);
            tabContent.appendChild(riskSection);
        }
        
        tabContentsDiv.appendChild(tabContent);
    }
    
    function createTableRow(label, content) {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-100';
        
        const labelCell = document.createElement('td');
        labelCell.className = 'py-3 px-2 text-sm font-medium text-gray-500 w-40';
        labelCell.textContent = label;
        
        const contentCell = document.createElement('td');
        contentCell.className = 'py-3 px-2 text-sm text-gray-800';
        
        // content가 노드인지 확인하고 처리
        if (content instanceof Node) {
            contentCell.appendChild(content);
        } else {
            contentCell.textContent = content;
        }
        
        row.appendChild(labelCell);
        row.appendChild(contentCell);
        
        return row;
    }
    
    function createStatusSpan(text, colorClass) {
        const span = document.createElement('span');
        span.className = `${colorClass} font-medium`;
        span.textContent = text;
        return span;
    }
    
    function createRiskAssessmentSection(riskLevel, riskMessages) {
        // 위험도 컨테이너 생성
        const container = document.createElement('div');
        container.className = 'mt-6 border-t border-gray-200 pt-4';
        
        // 위험도 헤더
        const header = document.createElement('h3');
        header.className = 'text-lg font-medium text-gray-700 mb-2';
        header.textContent = '위험도 평가';
        container.appendChild(header);
        
        // 색상 계산 (0-100 사이의 위험도를 기반으로 색상 결정)
        // 0: 초록색(안전), 50: 노란색(주의), 100: 빨간색(위험)
        const getColorFromRiskLevel = (level) => {
            if (level <= 0) return 'text-green-600';
            if (level < 20) return 'text-green-500';
            if (level < 40) return 'text-yellow-500';
            if (level < 60) return 'text-orange-500';
            if (level < 80) return 'text-red-500';
            return 'text-red-600';
        };
        
        // 위험도 표시기 생성
        const riskIndicator = document.createElement('div');
        riskIndicator.className = 'mb-2';
        
        const riskValueDisplay = document.createElement('div');
        const colorClass = getColorFromRiskLevel(riskLevel);
        riskValueDisplay.className = `text-xl font-bold ${colorClass} mb-1`;
        
        // 위험도 레벨에 따른 텍스트 표시
        let riskText = '';
        if (riskLevel <= 10) {
            riskText = '안전';
        } else if (riskLevel <= 30) {
            riskText = '낮은 위험';
        } else if (riskLevel <= 60) {
            riskText = '중간 위험';
        } else if (riskLevel <= 80) {
            riskText = '높은 위험';
        } else {
            riskText = '매우 위험';
        }
        
        // 위험 점수 텍스트 표시
        riskValueDisplay.textContent = `${riskText} (${riskLevel}점)`;
        riskIndicator.appendChild(riskValueDisplay);

        // ✅ 여기서 진행 막대(progressContainer) 관련 부분은 삭제!

        container.appendChild(riskIndicator);

        
        // 위험 메시지가 있는 경우에만 표시
        if (riskMessages && riskMessages.length > 0) {
            const messageHeader = document.createElement('h4');
            messageHeader.className = 'text-sm font-medium text-gray-700 mt-3 mb-1';
            messageHeader.textContent = '주의 사항:';
            container.appendChild(messageHeader);
            
            const messageList = document.createElement('ul');
            messageList.className = 'list-disc pl-5 space-y-1';
            
            riskMessages.forEach(message => {
                const listItem = document.createElement('li');
                listItem.className = `text-sm ${colorClass}`;
                listItem.textContent = message;
                messageList.appendChild(listItem);
            });
            
            container.appendChild(messageList);
        }
        
        return container;
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
        const contents = document.querySelectorAll('#tab-contents div[data-index]');
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