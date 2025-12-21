export interface RadarAttackPair {
    id: string;
    origin: {
        code: string;
        name: string;
    };
    target: {
        code: string;
        name: string;
    };
    magnitude: number;
}

interface FetchOptions {
    dateRange?: string;
    limit?: number;
}

const RADAR_ENDPOINT = 'https://api.cloudflare.com/client/v4/radar/attacks/layer7/top/attacks';

const extractLocationCode = (dimension: any): string | null => {
    if (!dimension) return null;
    return (
        dimension.location ||
        dimension.location_alpha2 ||
        dimension.alpha2 ||
        dimension.code ||
        dimension.country ||
        dimension.value ||
        null
    );
};

const extractLocationName = (dimension: any): string => {
    if (!dimension) return 'Unknown';
    return dimension.name || dimension.location_name || dimension.country || dimension.location || 'Unknown';
};

const toNumber = (value: unknown): number => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
};

export const fetchRadarAttackPairs = async (options: FetchOptions = {}): Promise<RadarAttackPair[]> => {
    const token = import.meta.env.VITE_RADAR_API_TOKEN;
    if (!token) {
        throw new Error('Set VITE_RADAR_API_TOKEN in your environment to enable the live Radar globe.');
    }

    const params = new URLSearchParams({
        dateRange: options.dateRange ?? '30m',
        limit: String(options.limit ?? 12),
        metric: 'REQUESTS',
        format: 'json'
    });

    const response = await fetch(`${RADAR_ENDPOINT}?${params.toString()}`, {
        headers: {
            Authorization: `Bearer ${token}`,
        }
    });

    if (!response.ok) {
        const message = await response.text();
        throw new Error(`Radar API ${response.status}: ${message || 'Unknown error'}`);
    }

    const payload = await response.json();
    const rows: any[] = payload?.result?.top_0 ?? [];

    return rows
        .map((entry, idx): RadarAttackPair | null => {
            const origin = entry?.dimensions?.origin ?? entry?.dimensions?.source;
            const target = entry?.dimensions?.target ?? entry?.dimensions?.destination;
            const originCode = extractLocationCode(origin);
            const targetCode = extractLocationCode(target);
            if (!originCode || !targetCode) {
                return null;
            }

            const magnitude = toNumber(entry?.value ?? entry?.sum ?? entry?.count ?? entry?.metrics?.requests);

            return {
                id: entry?.id ?? `${originCode}-${targetCode}-${idx}`,
                origin: {
                    code: originCode.toUpperCase(),
                    name: extractLocationName(origin)
                },
                target: {
                    code: targetCode.toUpperCase(),
                    name: extractLocationName(target)
                },
                magnitude
            };
        })
        .filter((item): item is RadarAttackPair => Boolean(item));
};
