CREATE TABLE applicant_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE NOT NULL REFERENCES business_profiles(id) ON DELETE CASCADE,
    full_legal_name TEXT CHECK (char_length(full_legal_name) BETWEEN 2 AND 120),
    date_of_birth DATE,
    nid_number TEXT CHECK (nid_number ~ '^[0-9]{10}$|^[0-9]{13}$|^[0-9]{17}$'),
    address TEXT CHECK (char_length(address) BETWEEN 2 AND 300),
    nominee_name TEXT CHECK (char_length(nominee_name) BETWEEN 2 AND 120),
    nominee_relation TEXT CHECK (char_length(nominee_relation) BETWEEN 2 AND 80),
    trade_licence TEXT CHECK (char_length(trade_licence) BETWEEN 1 AND 100),
    years_in_business INTEGER CHECK (years_in_business BETWEEN 0 AND 80),
    declared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
