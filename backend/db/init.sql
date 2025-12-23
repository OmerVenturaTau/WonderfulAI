-- Initialize Pharmacy Database Schema and Seed Data

-- Enable pg_trgm extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create tables
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  full_name TEXT,
  phone TEXT,
  email TEXT,
  preferred_language TEXT
);

CREATE TABLE IF NOT EXISTS medications (
  med_id TEXT PRIMARY KEY,
  brand_name TEXT,
  generic_name TEXT,
  active_ingredients TEXT,
  form TEXT,
  strength TEXT,
  rx_required INTEGER,
  standard_directions TEXT,
  warnings TEXT,
  contraindications TEXT
);

CREATE TABLE IF NOT EXISTS stores (
  store_id TEXT PRIMARY KEY,
  city TEXT,
  name TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
  store_id TEXT,
  med_id TEXT,
  quantity INTEGER,
  last_updated TEXT,
  PRIMARY KEY (store_id, med_id)
);

CREATE TABLE IF NOT EXISTS prescriptions (
  prescription_id TEXT PRIMARY KEY,
  user_id TEXT,
  med_id TEXT,
  directions TEXT,
  refills_remaining INTEGER,
  expires_at TEXT
);

CREATE TABLE IF NOT EXISTS refill_requests (
  refill_request_id TEXT PRIMARY KEY,
  prescription_id TEXT,
  user_id TEXT,
  status TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_stats (
  tool_name TEXT PRIMARY KEY,
  call_count BIGINT NOT NULL DEFAULT 0
);

-- Seed data: 10 users
INSERT INTO users (user_id, full_name, phone, email, preferred_language) VALUES
('1001', 'User 1001', '+972-50-00001001', 'user1001@example.com', 'en'),
('1002', 'User 1002', '+972-50-00001002', 'user1002@example.com', 'he'),
('1003', 'User 1003', '+972-50-00001003', 'user1003@example.com', 'en'),
('1004', 'User 1004', '+972-50-00001004', 'user1004@example.com', 'he'),
('1005', 'User 1005', '+972-50-00001005', 'user1005@example.com', 'en'),
('1006', 'User 1006', '+972-50-00001006', 'user1006@example.com', 'he'),
('1007', 'User 1007', '+972-50-00001007', 'user1007@example.com', 'en'),
('1008', 'User 1008', '+972-50-00001008', 'user1008@example.com', 'he'),
('1009', 'User 1009', '+972-50-00001009', 'user1009@example.com', 'en'),
('1010', 'User 1010', '+972-50-00001010', 'user1010@example.com', 'he')
ON CONFLICT (user_id) DO NOTHING;

-- Seed data: Stores
INSERT INTO stores (store_id, city, name) VALUES
('STORE_TLV_01', 'Tel Aviv', 'Wonderful Pharmacy TLV Center'),
('STORE_TLV_02', 'Tel Aviv', 'Wonderful Pharmacy Dizengoff'),
('STORE_JLM_01', 'Jerusalem', 'Wonderful Pharmacy JLM'),
('STORE_HFA_01', 'Haifa', 'Wonderful Pharmacy Haifa'),
('STORE_BRS_01', 'Beer Sheva', 'Wonderful Pharmacy Beer Sheva')
ON CONFLICT (store_id) DO NOTHING;

-- Seed data: 15 Medications - diverse categories
INSERT INTO medications (
  med_id, brand_name, generic_name, active_ingredients, form, strength, rx_required,
  standard_directions, warnings, contraindications
) VALUES
-- Pain Relief (OTC)
('MED001', 'Nurofen', 'Ibuprofen', 'Ibuprofen', 'Tablet', '200 mg', 0,
 'Standard directions (adult): 200 mg every 6–8 hours as needed. Do not exceed 1200 mg/day without medical supervision.',
 'May cause stomach irritation. Avoid combining with other NSAIDs. Follow package leaflet.',
 'History of severe allergy to NSAIDs; active GI bleeding.'),
('MED002', 'Acamol', 'Paracetamol', 'Paracetamol', 'Tablet', '500 mg', 0,
 'Standard directions (adult): 500–1000 mg every 4–6 hours as needed. Do not exceed 4000 mg/day.',
 'Avoid combining with other products containing paracetamol. Follow package leaflet.',
 'Severe liver disease.'),
('MED003', 'Advil', 'Ibuprofen', 'Ibuprofen', 'Capsule', '400 mg', 0,
 'Standard directions (adult): 400 mg every 6–8 hours as needed. Do not exceed 1200 mg/day.',
 'May cause stomach irritation. Follow package leaflet.',
 'History of severe allergy to NSAIDs; active GI bleeding.'),

-- Cholesterol (Prescription)
('MED004', 'Lipitor', 'Atorvastatin', 'Atorvastatin', 'Tablet', '20 mg', 1,
 'Standard directions: take once daily as prescribed. Follow prescription label.',
 'Prescription medicine. Do not start/stop without clinician guidance. Follow leaflet.',
 'Active liver disease; pregnancy (per leaflet).'),
('MED005', 'Crestor', 'Rosuvastatin', 'Rosuvastatin', 'Tablet', '10 mg', 1,
 'Standard directions: take once daily as prescribed. Follow prescription label.',
 'Prescription medicine. May cause muscle pain. Follow leaflet.',
 'Active liver disease; pregnancy.'),

-- Antibiotics (Prescription)
('MED006', 'Augmentin', 'Amoxicillin/Clavulanate', 'Amoxicillin, Clavulanate', 'Tablet', '875/125 mg', 1,
 'Standard directions: take exactly as prescribed and complete the course. Follow prescription label.',
 'Prescription antibiotic. Allergic reactions possible. Follow leaflet.',
 'Penicillin allergy.'),
('MED007', 'Azithromycin', 'Azithromycin', 'Azithromycin', 'Tablet', '500 mg', 1,
 'Standard directions: take as prescribed, usually once daily. Complete the full course.',
 'Prescription antibiotic. May cause stomach upset. Follow leaflet.',
 'Severe liver disease.'),

-- Allergy (OTC)
('MED008', 'Zyrtec', 'Cetirizine', 'Cetirizine', 'Tablet', '10 mg', 0,
 'Standard directions (adult): 10 mg once daily. May cause drowsiness in some people.',
 'May cause drowsiness. Follow leaflet.',
 'Severe allergy to cetirizine.'),
('MED009', 'Claritin', 'Loratadine', 'Loratadine', 'Tablet', '10 mg', 0,
 'Standard directions (adult): 10 mg once daily. Non-drowsy formula.',
 'Generally well tolerated. Follow leaflet.',
 'Severe allergy to loratadine.'),

-- Blood Pressure (Prescription)
('MED010', 'Norvasc', 'Amlodipine', 'Amlodipine', 'Tablet', '5 mg', 1,
 'Standard directions: take once daily as prescribed. Follow prescription label.',
 'Prescription medicine. May cause dizziness. Follow leaflet.',
 'Severe low blood pressure.'),
('MED011', 'Lisinopril', 'Lisinopril', 'Lisinopril', 'Tablet', '10 mg', 1,
 'Standard directions: take once daily as prescribed. Follow prescription label.',
 'Prescription medicine. May cause dry cough. Follow leaflet.',
 'Pregnancy; history of angioedema.'),

-- Diabetes (Prescription)
('MED012', 'Metformin', 'Metformin', 'Metformin', 'Tablet', '500 mg', 1,
 'Standard directions: take as prescribed, usually twice daily with meals. Follow prescription label.',
 'Prescription medicine. May cause stomach upset initially. Follow leaflet.',
 'Severe kidney disease; severe liver disease.'),

-- Antacid (OTC)
('MED013', 'Gaviscon', 'Aluminum Hydroxide, Magnesium Carbonate', 'Aluminum Hydroxide, Magnesium Carbonate', 'Liquid', '10 ml', 0,
 'Standard directions: take 10-20 ml after meals and at bedtime as needed.',
 'Generally well tolerated. Follow leaflet.',
 'Severe kidney disease.'),
('MED014', 'Rennie', 'Calcium Carbonate, Magnesium Carbonate', 'Calcium Carbonate, Magnesium Carbonate', 'Tablet', '680 mg', 0,
 'Standard directions: chew 1-2 tablets as needed, up to 11 tablets per day.',
 'Generally well tolerated. Follow leaflet.',
 'Severe kidney disease.'),

-- Cold & Flu (OTC)
('MED015', 'Coldrex', 'Paracetamol, Pseudoephedrine, Dextromethorphan', 'Paracetamol, Pseudoephedrine, Dextromethorphan', 'Powder', '1000/60/30 mg', 0,
 'Standard directions: dissolve one sachet in hot water, take every 4-6 hours as needed.',
 'May cause drowsiness. Do not exceed 4 sachets per day. Follow leaflet.',
 'Severe liver disease; high blood pressure; MAOI use.')
ON CONFLICT (med_id) DO NOTHING;

-- Seed data: Inventory - varied stock levels across stores
INSERT INTO inventory (store_id, med_id, quantity, last_updated) VALUES
-- Tel Aviv Center Store
('STORE_TLV_01', 'MED001', 25, NOW()::TEXT),  -- Nurofen - well stocked
('STORE_TLV_01', 'MED002', 8, NOW()::TEXT),   -- Acamol - low stock
('STORE_TLV_01', 'MED003', 15, NOW()::TEXT),  -- Advil - good stock
('STORE_TLV_01', 'MED004', 0, NOW()::TEXT),   -- Lipitor - out of stock
('STORE_TLV_01', 'MED005', 5, NOW()::TEXT),   -- Crestor - low stock
('STORE_TLV_01', 'MED006', 12, NOW()::TEXT),  -- Augmentin - good stock
('STORE_TLV_01', 'MED007', 0, NOW()::TEXT),   -- Azithromycin - out of stock
('STORE_TLV_01', 'MED008', 30, NOW()::TEXT),  -- Zyrtec - well stocked
('STORE_TLV_01', 'MED009', 20, NOW()::TEXT),  -- Claritin - good stock
('STORE_TLV_01', 'MED010', 3, NOW()::TEXT),   -- Norvasc - low stock
('STORE_TLV_01', 'MED011', 0, NOW()::TEXT),   -- Lisinopril - out of stock
('STORE_TLV_01', 'MED012', 18, NOW()::TEXT),  -- Metformin - good stock
('STORE_TLV_01', 'MED013', 10, NOW()::TEXT),  -- Gaviscon - good stock
('STORE_TLV_01', 'MED014', 22, NOW()::TEXT),  -- Rennie - good stock
('STORE_TLV_01', 'MED015', 6, NOW()::TEXT),   -- Coldrex - low stock

-- Tel Aviv Dizengoff Store
('STORE_TLV_02', 'MED001', 0, NOW()::TEXT),   -- Nurofen - out of stock
('STORE_TLV_02', 'MED002', 15, NOW()::TEXT),  -- Acamol - good stock
('STORE_TLV_02', 'MED003', 0, NOW()::TEXT),   -- Advil - out of stock
('STORE_TLV_02', 'MED004', 8, NOW()::TEXT),   -- Lipitor - low stock
('STORE_TLV_02', 'MED005', 12, NOW()::TEXT),  -- Crestor - good stock
('STORE_TLV_02', 'MED008', 0, NOW()::TEXT),   -- Zyrtec - out of stock
('STORE_TLV_02', 'MED009', 25, NOW()::TEXT),  -- Claritin - well stocked
('STORE_TLV_02', 'MED011', 7, NOW()::TEXT),   -- Lisinopril - low stock
('STORE_TLV_02', 'MED013', 0, NOW()::TEXT),   -- Gaviscon - out of stock
('STORE_TLV_02', 'MED014', 18, NOW()::TEXT),  -- Rennie - good stock

-- Jerusalem Store
('STORE_JLM_01', 'MED001', 10, NOW()::TEXT),  -- Nurofen - good stock
('STORE_JLM_01', 'MED002', 0, NOW()::TEXT),   -- Acamol - out of stock
('STORE_JLM_01', 'MED004', 6, NOW()::TEXT),   -- Lipitor - low stock
('STORE_JLM_01', 'MED006', 0, NOW()::TEXT),   -- Augmentin - out of stock
('STORE_JLM_01', 'MED007', 9, NOW()::TEXT),   -- Azithromycin - low stock
('STORE_JLM_01', 'MED008', 20, NOW()::TEXT),  -- Zyrtec - good stock
('STORE_JLM_01', 'MED010', 14, NOW()::TEXT),  -- Norvasc - good stock
('STORE_JLM_01', 'MED011', 11, NOW()::TEXT),  -- Lisinopril - good stock
('STORE_JLM_01', 'MED012', 0, NOW()::TEXT),  -- Metformin - out of stock
('STORE_JLM_01', 'MED015', 4, NOW()::TEXT),   -- Coldrex - low stock

-- Haifa Store
('STORE_HFA_01', 'MED001', 18, NOW()::TEXT),  -- Nurofen - good stock
('STORE_HFA_01', 'MED003', 12, NOW()::TEXT),  -- Advil - good stock
('STORE_HFA_01', 'MED005', 0, NOW()::TEXT),   -- Crestor - out of stock
('STORE_HFA_01', 'MED008', 0, NOW()::TEXT),   -- Zyrtec - out of stock
('STORE_HFA_01', 'MED009', 16, NOW()::TEXT),  -- Claritin - good stock
('STORE_HFA_01', 'MED012', 7, NOW()::TEXT),   -- Metformin - low stock
('STORE_HFA_01', 'MED014', 0, NOW()::TEXT),   -- Rennie - out of stock

-- Beer Sheva Store
('STORE_BRS_01', 'MED002', 20, NOW()::TEXT),  -- Acamol - good stock
('STORE_BRS_01', 'MED004', 0, NOW()::TEXT),   -- Lipitor - out of stock
('STORE_BRS_01', 'MED006', 5, NOW()::TEXT),   -- Augmentin - low stock
('STORE_BRS_01', 'MED010', 0, NOW()::TEXT),   -- Norvasc - out of stock
('STORE_BRS_01', 'MED013', 15, NOW()::TEXT),  -- Gaviscon - good stock
('STORE_BRS_01', 'MED015', 0, NOW()::TEXT)    -- Coldrex - out of stock
ON CONFLICT (store_id, med_id) DO NOTHING;

-- Seed data: Prescriptions - various scenarios
INSERT INTO prescriptions (prescription_id, user_id, med_id, directions, refills_remaining, expires_at) VALUES
-- Active prescriptions with refills
('RX-0001', '1003', 'MED004', 'Take 1 tablet once daily as prescribed.', 2, (CURRENT_DATE + INTERVAL '30 days')::TEXT),
('RX-0002', '1005', 'MED010', 'Take 1 tablet once daily in the morning.', 5, (CURRENT_DATE + INTERVAL '90 days')::TEXT),
('RX-0003', '1007', 'MED012', 'Take 1 tablet twice daily with meals.', 3, (CURRENT_DATE + INTERVAL '60 days')::TEXT),
('RX-0004', '1009', 'MED005', 'Take 1 tablet once daily at bedtime.', 1, (CURRENT_DATE + INTERVAL '15 days')::TEXT),
('RX-0005', '1011', 'MED011', 'Take 1 tablet once daily as prescribed.', 4, (CURRENT_DATE + INTERVAL '45 days')::TEXT),

-- Prescriptions with no refills remaining
('RX-0006', '1003', 'MED006', 'Take 1 tablet twice daily. Complete the full course.', 0, (CURRENT_DATE + INTERVAL '20 days')::TEXT),
('RX-0007', '1001', 'MED007', 'Take 1 tablet once daily for 5 days.', 0, (CURRENT_DATE + INTERVAL '10 days')::TEXT),

-- Prescriptions expiring soon (within 7 days)
('RX-0008', '1002', 'MED004', 'Take 1 tablet once daily.', 1, (CURRENT_DATE + INTERVAL '5 days')::TEXT),
('RX-0009', '1004', 'MED010', 'Take 1 tablet once daily.', 2, (CURRENT_DATE + INTERVAL '3 days')::TEXT),

-- Prescriptions expiring in medium term (8-30 days)
('RX-0010', '1006', 'MED005', 'Take 1 tablet once daily.', 0, (CURRENT_DATE + INTERVAL '12 days')::TEXT),
('RX-0011', '1008', 'MED011', 'Take 1 tablet once daily.', 3, (CURRENT_DATE + INTERVAL '25 days')::TEXT),
('RX-0012', '1010', 'MED012', 'Take 1 tablet twice daily with meals.', 2, (CURRENT_DATE + INTERVAL '18 days')::TEXT),

-- Multiple prescriptions for same user
('RX-0013', '1013', 'MED004', 'Take 1 tablet once daily.', 1, (CURRENT_DATE + INTERVAL '40 days')::TEXT),
('RX-0014', '1013', 'MED010', 'Take 1 tablet once daily in the morning.', 2, (CURRENT_DATE + INTERVAL '35 days')::TEXT),
('RX-0015', '1013', 'MED011', 'Take 1 tablet once daily.', 0, (CURRENT_DATE + INTERVAL '22 days')::TEXT),

-- Prescriptions for different medication types
('RX-0016', '1015', 'MED006', 'Take 1 tablet twice daily with food. Complete full course.', 1, (CURRENT_DATE + INTERVAL '28 days')::TEXT),
('RX-0017', '1012', 'MED005', 'Take 1 tablet once daily at bedtime.', 4, (CURRENT_DATE + INTERVAL '50 days')::TEXT),
('RX-0018', '1014', 'MED012', 'Take 1 tablet twice daily with meals.', 2, (CURRENT_DATE + INTERVAL '33 days')::TEXT)
ON CONFLICT (prescription_id) DO NOTHING;

