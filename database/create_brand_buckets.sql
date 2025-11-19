-- Create brand_buckets table
-- Brand buckets are used to group brands into custom categories with colors

CREATE TABLE IF NOT EXISTS brand_buckets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(7) NOT NULL DEFAULT '#667eea',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Add brand_bucket_id to brand table
ALTER TABLE brand 
ADD COLUMN brand_bucket_id INT NULL,
ADD CONSTRAINT fk_brand_bucket 
    FOREIGN KEY (brand_bucket_id) 
    REFERENCES brand_buckets(id) 
    ON DELETE SET NULL;

-- Create index for better query performance
CREATE INDEX idx_brand_bucket_id ON brand(brand_bucket_id);

-- Insert some default brand buckets
INSERT INTO brand_buckets (name, color, description) VALUES
    ('Priority A', '#10b981', 'High priority brands - focus on growth'),
    ('Priority B', '#3b82f6', 'Medium priority brands - maintain'),
    ('Priority C', '#f59e0b', 'Low priority brands - monitor'),
    ('New Acquisitions', '#8b5cf6', 'Recently acquired brands'),
    ('Legacy', '#6b7280', 'Older brands in portfolio'),
    ('Seasonal', '#ec4899', 'Seasonal product brands');

SELECT 'Brand buckets table created successfully!' as message;

