-- Generated from ocr_service.db; run in an empty MySQL 8+ utf8mb4 database.

SET NAMES utf8mb4;

CREATE TABLE ocr_files (
	id VARCHAR(32) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(100) NOT NULL, 
	media_type VARCHAR(40) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size INTEGER NOT NULL, 
	page_count INTEGER NOT NULL, 
	active_job_id VARCHAR(32), 
	generation INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_ocr_files_owner_id ON ocr_files (owner_id);

CREATE TABLE ocr_audit_log (
	id VARCHAR(32) NOT NULL, 
	actor_id VARCHAR(128) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	resource_id VARCHAR(32) NOT NULL, 
	detail JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_ocr_audit_log_actor_id ON ocr_audit_log (actor_id);

CREATE TABLE ocr_jobs (
	id VARCHAR(32) NOT NULL, 
	file_id VARCHAR(32) NOT NULL, 
	generation INTEGER NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	options JSON NOT NULL, 
	attempts INTEGER NOT NULL, 
	lease_token VARCHAR(32), 
	lease_until DATETIME, 
	available_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	finished_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(file_id) REFERENCES ocr_files (id)
);

CREATE INDEX ix_ocr_jobs_owner_id ON ocr_jobs (owner_id);

CREATE INDEX ix_ocr_queue ON ocr_jobs (status, available_at, lease_until);

CREATE INDEX ix_ocr_jobs_file_id ON ocr_jobs (file_id);

CREATE TABLE ocr_pages (
	id VARCHAR(32) NOT NULL, 
	job_id VARCHAR(32) NOT NULL, 
	page_no INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	revision INTEGER NOT NULL, 
	result JSON, 
	error VARCHAR(80), 
	PRIMARY KEY (id), 
	UNIQUE (job_id, page_no), 
	FOREIGN KEY(job_id) REFERENCES ocr_jobs (id)
);

CREATE INDEX ix_ocr_pages_job_id ON ocr_pages (job_id);

CREATE TABLE pdf_text_index (
	id VARCHAR(32) NOT NULL, 
	file_id VARCHAR(32) NOT NULL, 
	page_no INTEGER NOT NULL, 
	job_id VARCHAR(32) NOT NULL, 
	revision INTEGER NOT NULL, 
	content LONGTEXT NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (file_id, page_no), 
	FOREIGN KEY(file_id) REFERENCES ocr_files (id), 
	FOREIGN KEY(job_id) REFERENCES ocr_jobs (id)
);

CREATE FULLTEXT INDEX ft_pdf_text_content ON pdf_text_index (content) WITH PARSER ngram;

CREATE INDEX ix_pdf_text_index_file_id ON pdf_text_index (file_id);