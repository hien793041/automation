# Ý tưởng di chuyển tìm Gem - Random Walk Humanize

## Nguyên tắc cốt lõi

- Chỉ dùng **4 phím mũi tên** (↑ ↓ ← →)
- Mỗi lần bấm = di chuyển **1 ô liền kề**
- **Không quay lại ô đã đi** (trừ khi bị kẹt)
- **Giới hạn bán kính 50km** từ nhà (tâm)

---

## Cơ chế di chuyển

### 1. Bước ngẫu nhiên
Từ ô hiện tại, chọn ngẫu nhiên 1 trong 4 hướng:
- Kiểm tra ô đích có trong bán kính 50km không
- Kiểm tra ô đích đã đi qua chưa
- Nếu OK → di chuyển
- Nếu FAIL → chọn hướng khác

### 2. Bị kẹt (dead end)
Khi cả 4 hướng đều không đi được:
- **Quay lui 1 bước** (bấm phím ngược hướng vừa đi)
- Từ ô cũ, chọn lại hướng ngẫu nhiên khác
- Lặp lại cho đến khi thoát khỏi dead end

### 3. Điều kiện dừng
- Tìm thấy icon gem → dừng, báo vị trí
- Hoặc cover hết tất cả ô trong bán kính 50km → kết thúc (không có gem)

---

## Ví dụ minh họa (Nhà ở tâm)

```
Bước 0:  [Nhà] ──→ chọn random → 

Bước 1:  [Nhà] → [→] ──→ chọn random →
         (đã visit)

Bước 2:  [Nhà] → [→] → [→] ──→ chọn random →
         (đã visit)  (đã visit)

Bước 3:  [Nhà] → [→] → [→]
                  ↑
                 [↑]  ←── chọn ↑ (random)
         (đã visit)

Bước 4:  [Nhà] → [→] → [→]
                  ↑
                 [↑] → [→]  ←── chọn → (random)
         (đã visit)  (đã visit)

Bước 5:  [Nhà] → [→] → [→]
                  ↑
                 [↑] → [→] → [↓]  ←── chọn ↓ (random)
         (đã visit)  (đã visit)  (đã visit)

Bước 6:  Bị kẹt! Cả 4 hướng đều đã visit hoặc ngoài bán kính
          → Quay lui: bấm [←] (ngược hướng vừa đi)

Bước 7:  Quay về ô [→], chọn lại random hướng khác...
```

---

## Trạng thái cần nhớ

| Dữ liệu | Mục đích |
|---------|----------|
| `visited` set | Các ô đã đi qua (không quay lại) |
| `current_pos` | Tọa độ hiện tại (x, y) |
| `home_pos` | Tọa độ nhà (0, 0) |
| `radius` | Bán kính giới hạn (50km) |

---

## Ưu điểm

- **Tự nhiên như người thật**: Không rập khuôn, không máy móc
- **Không cần tính toán phức tạp**: Chỉ random + check điều kiện
- **Không bị lặp vô hạn**: Nhờ visited set và backtrack
- **Cover toàn bộ**: Cuối cùng sẽ đi hết nếu kiên nhẫn đủ

## Nhược điểm

- **Không tối ưu**: Có thể đi vòng vòng lâu trước khi tìm được gem
- **Cần nhớ nhiều**: Càng xa tâm, visited set càng lớn
- **Không đảm bảo tìm gần nhất trước**: Có thể bỏ qua gem gần vì random

---

## Ghi chú cho implement

- Mỗi ô vuông = 1 đơn vị khoảng cách (1km)
- Khoảng cách từ nhà: `sqrt(x² + y²) <= 50`
- Phím mũi tên mapping: ↑(y+1), ↓(y-1), ←(x-1), →(x+1)
- Backtrack: lưu lại hướng vừa đi để biết phím ngược
