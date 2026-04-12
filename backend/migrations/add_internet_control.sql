-- Add internet access tracking to message_verifications
ALTER TABLE message_verifications ADD COLUMN internet_allowed BOOLEAN DEFAULT 0;
ALTER TABLE message_verifications ADD COLUMN internet_reason TEXT;
ALTER TABLE message_verifications ADD COLUMN internet_violation TEXT;
