import pathlib

p_writer = pathlib.Path("stage_2_writer.py")
content = p_writer.read_text(encoding="utf-8")

bad_loop = """    for tf in trace_files:
        batch_id = tf.stem.replace("trace_", "")
        print(f"⏳ {batch_id}")
        ok, _ = write_batch(tf, pending_dir, manifest, args.operator, args, dry_run=args.dry_run)"""

good_loop = """    for tf in trace_files:
        batch_id = tf.stem.replace("trace_", "")
        print(f"⏳ {batch_id}")
        
        # Extract QA feedback from previous runs
        import json
        trace_data = json.loads(tf.read_text(encoding="utf-8"))
        feedback = trace_data.get("requeue_feedback")
        
        ok, _ = write_batch(tf, pending_dir, manifest, args.operator, args, qa_feedback=feedback, dry_run=args.dry_run)"""

content = content.replace(bad_loop, good_loop)
p_writer.write_text(content, encoding="utf-8")
print("✅ QA Feedback loop successfully wired to Writer agent.")
