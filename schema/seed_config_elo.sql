INSERT INTO config (key, value, description) VALUES
('elo_k_factor', '20', 'How much a single game result moves a team rating'),
('mov_cap', '28', 'Point margin above which additional margin stops adding weight'),
('preseason_blend_weight', '0.5', 'Weight on talent composite vs prior-year Elo in preseason prior'),
('fcs_baseline_rating', '1200', 'Flat Elo assigned to any FCS opponent; never dynamically updated');