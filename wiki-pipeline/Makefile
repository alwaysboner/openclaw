MONTH       ?= $(shell date +%Y-%m)
WIKI_ROOT   := $(HOME)/.openclaw/wiki/main
TRACES_DIR  := $(WIKI_ROOT)/transcripts/processed/traces
PENDING_DIR := $(WIKI_ROOT)/promoted-pending
MANIFEST    := $(WIKI_ROOT)/pages_manifest.json
CHUNKS_DIR  := $(HOME)/.openclaw/workspace/uploads/Chunks
OPERATOR    ?= Jason

.DEFAULT_GOAL := help

help:
	@echo "📝 OpenClaw Wiki Pipeline v6.1 (Newsroom Arch)"
	@echo "Usage: make requeue BATCH=YYYY_MM_batch_NNN"

chunk:
	~/openclaw-env/bin/python3 stage_1_chunker.py --month $(MONTH) --chunks-dir $(CHUNKS_DIR) --traces-dir $(TRACES_DIR)

write:
	~/openclaw-env/bin/python3 stage_2_writer.py --month $(MONTH) --manifest $(MANIFEST) --operator $(OPERATOR) --traces-dir $(TRACES_DIR) --pending-dir $(PENDING_DIR)

qa:
	~/openclaw-env/bin/python3 stage_3_qa.py --month $(MONTH) --traces-dir $(TRACES_DIR) --pending-dir $(PENDING_DIR) --qa-model "gemini-2.5-flash"

enforce:
	~/openclaw-env/bin/python3 stage_3_retry_enforcer.py --traces-dir $(TRACES_DIR) --month $(MONTH)

promote:
	~/openclaw-env/bin/python3 promote_wiki_pages.py --pending-dir $(PENDING_DIR) --wiki-root $(WIKI_ROOT) --month $(MONTH)

index:
	~/openclaw-env/bin/python3 stage_5_index_builder.py --wiki-root $(WIKI_ROOT) --month $(MONTH)

requeue:
	@test -n "$(BATCH)" || (echo "Usage: make requeue BATCH=YYYY_MM_batch_NNN" && exit 1)
	$(eval MONTH := $(shell echo $(BATCH) | grep -oP '^\d{4}_\d{2}' | tr _ -))
	~/openclaw-env/bin/python3 stage_2_writer.py --month $(MONTH) --manifest $(MANIFEST) --operator $(OPERATOR) --primary-model "gemini-2.5-flash" --quality-model "gemini-2.5-pro" --batch-id $(BATCH)
	~/openclaw-env/bin/python3 stage_3_qa.py --month $(MONTH) --qa-model "gemini-2.5-flash" --batch-id $(BATCH)
	~/openclaw-env/bin/python3 stage_3_retry_enforcer.py --month $(MONTH) --batch-id $(BATCH)
