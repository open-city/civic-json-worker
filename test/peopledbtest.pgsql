CREATE TABLE attendance
(

    -- Check-in time with time zone, since we're global.
    datetime            TIMESTAMP WITH TIME ZONE,
    
    -- Like https://www.codeforamerica.org/api/organizations/Open-Oakland
    organization_url    TEXT,
    
    -- Optional name of meetup, event, etc.
    event_name          TEXT,
    
    -- Sometimes people answer informational questions when they check in.
    extras              JSON
);