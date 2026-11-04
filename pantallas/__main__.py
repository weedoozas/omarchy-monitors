import sys
if '--labels' in sys.argv[1:]:
    from .labels import run
    run()
else:
    from .app import main
    main()
