# Step 82F — Historical Forecast Source Requirements

A source suitable for Project Gridiron production backtesting should provide,
or allow reconstruction of:

- historical forecast issuance/retrieval timestamp;
- forecast valid time near NFL kickoff;
- temperature;
- sustained wind speed;
- precipitation probability or categorical condition;
- location/stadium matching;
- enough archive depth to cover the research seasons;
- licensing that permits programmatic research use.

The crucial requirement is **forecast vintage**. A historical weather archive
containing only final observed conditions is insufficient for production
promotion because it cannot recreate what was knowable before kickoff.

Preferred research target:
- snapshot approximately 2–4 hours before kickoff;
- forecast age under 24 hours;
- at least 80% temperature and wind coverage;
- explicit missingness instead of backfilling from observed conditions.
