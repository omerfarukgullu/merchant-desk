-- 0002_meeting_time_and_notify.sql
-- Toplantılara opsiyonel saat alanı ve arka plan hatırlatıcısının
-- (tray_app.py) "bu toplantı için zaten bildirim gönderdim" takibi.

ALTER TABLE meetings ADD COLUMN meeting_time TEXT;              -- 'HH:MM', NULL = saat belirtilmemiş
ALTER TABLE meetings ADD COLUMN reminder_sent_at TIMESTAMP;      -- NULL = bu toplantı için hatırlatma gönderilmedi
