# Báo cáo Benchmark

| Lần chạy | Độ trễ (giây) | Chi phí (USD) | Chất lượng | Ghi chú |
|---|---:|---:|---:|---|
| cơ sở | 12.95 |  | 4.0 | sources=0; trace_events=1; failure_rate=0.00; trace_provider=langsmith; degraded=false |
| đa tác nhân | 45.05 | 0.0013 | 10.0 | sources=5; trace_events=8; failure_rate=0.00; trace_provider=langsmith; degraded=false |
| cơ sở | 12.09 |  | 4.0 | sources=0; trace_events=1; failure_rate=0.00; trace_provider=langsmith; degraded=false |
| đa tác nhân | 17.59 | 0.0011 | 10.0 | sources=5; trace_events=8; failure_rate=0.00; trace_provider=langsmith; degraded=false |
| cơ sở | 5.04 |  | 4.0 | sources=0; trace_events=1; failure_rate=0.00; trace_provider=langsmith; degraded=false |
| đa tác nhân | 43.92 | 0.0009 | 10.0 | sources=5; trace_events=8; failure_rate=0.00; trace_provider=langsmith; degraded=false |

## Tóm tắt
- Tổng số lần chạy: 6
- Số lần chạy cơ sở: 3
- Số lần chạy đa tác nhân: 3
- Số lần chạy được trace bằng LangSmith: 6
- Số lần chạy được trace cục bộ: 0
- Số lần chạy ở trạng thái suy giảm: 0
- Diễn giải: độ trễ và chi phí càng thấp càng tốt, chất lượng càng cao càng tốt.

## Failure mode và cách khắc phục

Trong quá trình chạy benchmark, failure mode phổ biến là không đẩy được trace lên LangSmith dù API key hợp lệ.
Nguyên nhân chính là biến proxy môi trường bị cấu hình sai, ví dụ `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY=http://127.0.0.1:9`,
làm request tới `api.smith.langchain.com` bị từ chối với lỗi `WinError 10061`.
Khi đó, workflow vẫn chạy nhưng trace bị rơi về local hoặc mất log trên giao diện LangSmith.
Cách khắc phục là unset toàn bộ biến proxy trước khi chạy `multi-agent` và `benchmark`,
sau đó chạy lại và kiểm tra project `multi-agent-research-lab` trong khung thời gian gần nhất để xác nhận run đã xuất hiện.

## Giải thích cơ chế fallback

Hệ thống được thiết kế để không làm gãy pipeline khi provider bên ngoài gặp lỗi tạm thời, bằng cách dùng fallback theo từng lớp.
`LLM fallback`: nếu OpenAI lỗi mạng, timeout hoặc retry thất bại thì trả về nội dung local deterministic để workflow vẫn đi tiếp.
`Search fallback`: nếu Tavily không có key hoặc gọi API lỗi thì chuyển sang bộ nguồn mock cục bộ để vẫn tạo được `research_notes`.
`Tracing fallback`: nếu LangSmith không ghi trace được thì span vẫn được đo ở local, đồng thời đánh dấu `degraded=true`.
Tác động của fallback là tăng độ ổn định luồng chạy và tránh fail cứng khi demo, nhưng quality, cost và latency có thể lệch so với chế độ chạy provider thật 100%.
Vì vậy, khi đọc benchmark cần xem thêm `degraded` và `trace_provider` trong cột `Ghi chú` để phân biệt run thật và run có fallback.

## Link trace

- Project LangSmith: `multi-agent-research-lab`
- Link trace chính: 
`https://smith.langchain.com/public/de99ef6a-48ed-45a3-81e5-1921f0e62b53/r`
`https://smith.langchain.com/public/e510b649-c367-4406-8be7-17fa27832e4c/r`
`https://smith.langchain.com/public/344c110d-2bae-47cc-b6c6-a89c79f0e96e/r`
`https://smith.langchain.com/public/259fda94-10b4-4fd2-bbad-0ebf78f2af9e/r`
- Ghi chú: nếu người chấm không mở được link, hãy đính kèm thêm screenshot trace trong bài nộp.
![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)
![alt text](image-3.png)
![alt text](image-4.png)
![alt text](image-5.png)
![alt text](image-6.png)
![alt text](image-7.png)
![alt text](image-8.png)