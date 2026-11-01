"""The moderngl side of Fragments: compiling fragment programs and accumulating subframes into surfaces.

Everything here runs on the thread that created the `FragEngine`'s context (the render service's worker, a final
render's thread). `engine.py` owns the context and the caches, `program.py` a linked program with its uniform
table, `uniforms.py` the typed upload, `surfaces.py` the ping-pong accumulation buffers, `job.py` the service's job
protocol, `diagnostics.py` the mapping of driver errors back to source lines.
"""
