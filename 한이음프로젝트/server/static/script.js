document.getElementById('searchForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const query = this.query.value;
    const progressDiv = document.getElementById('progress');
    progressDiv.innerHTML = '';

    const eventSource = new EventSource(`/stream?query=${encodeURIComponent(query)}`);

    eventSource.onmessage = function (event) {
        const p = document.createElement('p');
        p.textContent = event.data;
        progressDiv.appendChild(p);

        // 완료되면 연결 종료
        if (event.data.includes('✅ 모든 검사 완료')) {
            eventSource.close();
        }
    };

    eventSource.onerror = function () {
        const p = document.createElement('p');
        p.textContent = '❌ 오류가 발생했습니다.';
        progressDiv.appendChild(p);
        eventSource.close();
    };
});
