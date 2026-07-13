.. KongFu-Chess documentation master file.

KongFu-Chess documentation
==========================

**KongFu-Chess** is a command-driven, real-time chess engine. You supply a starting
board and a list of commands (clicks, jumps, waits, prints); moves take physical
**travel time**, and you win by actually capturing the enemy king — there is no
check/checkmate.

The engine is built as a set of layers whose dependencies all point inward toward the
domain ``model``:

.. code-block:: text

   stdin
     -> ScriptParser      (split Board: / Commands:)
     -> BoardParser       (text -> model.Board, via PieceFactory)
     -> GameEngine        (public command boundary) + Controller
     -> ScriptRunner      (dispatch click / jump / wait / print board)
     -> BoardPrinter      (render board -> text)

Running
-------

Feed a ``Board:`` / ``Commands:`` document to ``main.py`` on stdin:

.. code-block:: bash

   python main.py < input.txt

Example document:

.. code-block:: text

   Board:
   wK . bK
   . . .
   Commands:
   click 50 50
   click 150 50
   wait 1000
   print board

Commands are ``click x y`` and ``jump x y`` (pixel coordinates), ``wait <ms>``, and
``print board``. A pixel maps to a cell by ``col = x // CELL_SIZE``, ``row = y // CELL_SIZE``.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   self

Domain model (``model``)
------------------------

The core: pure value objects and entities with no knowledge of rules, timing, rendering,
or input.

.. automodule:: model.position
   :members:

.. automodule:: model.piece
   :members:

.. automodule:: model.board
   :members:

.. automodule:: model.game_state
   :members:

Rules (``rules``)
-----------------

Stateless movement rules and read-only move validation.

.. automodule:: rules.piece_rules
   :members:

.. automodule:: rules.rule_engine
   :members:

Real-time movement (``realtime``)
---------------------------------

Movement over time and jump/dodge resolution. The board changes only on arrival.

.. automodule:: realtime.motion
   :members:

.. automodule:: realtime.real_time_arbiter
   :members:

Application service (``engine``)
--------------------------------

The public command boundary that orchestrates the other layers.

.. automodule:: engine.game_engine
   :members:

Input (``input``)
-----------------

Translating clicks into game commands.

.. automodule:: input.board_mapper
   :members:

.. automodule:: input.controller
   :members:

Text I/O (``text_io``)
----------------------

Parsing and rendering the text board format, and building pieces with stable ids.

.. automodule:: text_io.piece_factory
   :members:

.. automodule:: text_io.board_parser
   :members:

.. automodule:: text_io.board_printer
   :members:

Text-driven surface (``texttests``)
-----------------------------------

Parsing a script document and running its commands against the engine.

.. automodule:: texttests.script_parser
   :members:

.. automodule:: texttests.script_runner
   :members:

Entry point and configuration
-----------------------------

.. automodule:: main
   :members:

.. automodule:: config
   :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
