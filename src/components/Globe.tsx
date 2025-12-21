import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';
import { fetchRadarAttackPairs, RadarAttackPair } from '@utils/radarClient';
import { getCountryCoordinates } from '@utils/countryCoordinates';

type Severity = 'high' | 'medium' | 'low';

interface MarkerInput {
    id: string;
    code: string;
    country: string;
    lat: number;
    lon: number;
    severity: Severity;
}

interface ArcInput {
    id: string;
    originCode: string;
    targetCode: string;
    severity: Severity;
    magnitude: number;
}

const severityColors: Record<Severity, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#10b981',
};

const severityRank: Record<Severity, number> = { low: 1, medium: 2, high: 3 };

const fallbackMarkers: MarkerInput[] = [
    { id: 'US', code: 'US', country: 'United States', lat: 40.7128, lon: -74.006, severity: 'high' },
    { id: 'GB', code: 'GB', country: 'United Kingdom', lat: 51.5074, lon: -0.1278, severity: 'medium' },
    { id: 'JP', code: 'JP', country: 'Japan', lat: 35.6762, lon: 139.6503, severity: 'high' },
    { id: 'AU', code: 'AU', country: 'Australia', lat: -33.8688, lon: 151.2093, severity: 'low' },
    { id: 'RU', code: 'RU', country: 'Russia', lat: 55.7558, lon: 37.6173, severity: 'high' },
    { id: 'IN', code: 'IN', country: 'India', lat: 28.6139, lon: 77.209, severity: 'medium' },
    { id: 'BR', code: 'BR', country: 'Brazil', lat: -23.5505, lon: -46.6333, severity: 'low' },
    { id: 'FR', code: 'FR', country: 'France', lat: 48.8566, lon: 2.3522, severity: 'medium' },
];

const fallbackArcs: ArcInput[] = [
    { id: 'us-gb', originCode: 'US', targetCode: 'GB', severity: 'medium', magnitude: 12 },
    { id: 'gb-jp', originCode: 'GB', targetCode: 'JP', severity: 'high', magnitude: 15 },
    { id: 'jp-ru', originCode: 'JP', targetCode: 'RU', severity: 'high', magnitude: 11 },
    { id: 'ru-in', originCode: 'RU', targetCode: 'IN', severity: 'medium', magnitude: 9 },
    { id: 'au-jp', originCode: 'AU', targetCode: 'JP', severity: 'low', magnitude: 5 },
    { id: 'br-us', originCode: 'BR', targetCode: 'US', severity: 'medium', magnitude: 8 },
    { id: 'fr-gb', originCode: 'FR', targetCode: 'GB', severity: 'medium', magnitude: 7 },
    { id: 'in-au', originCode: 'IN', targetCode: 'AU', severity: 'low', magnitude: 4 },
];

// Convert lat/long to 3D coordinates on sphere
function latLongToVector3(lat: number, lon: number, radius: number) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);

    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);

    return new THREE.Vector3(x, y, z);
}

interface ThreatMarkerProps {
    position: THREE.Vector3;
    severity: Severity;
}

const ThreatMarker = ({ position, severity }: ThreatMarkerProps) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const glowRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (meshRef.current) {
            const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.4;
            meshRef.current.scale.set(scale, scale, scale);
        }
        if (glowRef.current) {
            const glowScale = 1.8 + Math.sin(state.clock.elapsedTime * 3) * 0.6;
            glowRef.current.scale.set(glowScale, glowScale, glowScale);
        }
    });

    return (
        <group position={position}>
            {/* Core marker */}
            <mesh ref={meshRef}>
                <sphereGeometry args={[0.02, 16, 16]} />
                <meshBasicMaterial 
                    color={severityColors[severity]} 
                    transparent 
                    opacity={1}
                />
            </mesh>
            {/* Inner glow */}
            <mesh scale={2}>
                <sphereGeometry args={[0.02, 16, 16]} />
                <meshBasicMaterial
                    color={severityColors[severity]}
                    transparent
                    opacity={0.6}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
            {/* Outer pulsing glow */}
            <mesh ref={glowRef}>
                <sphereGeometry args={[0.02, 16, 16]} />
                <meshBasicMaterial
                    color={severityColors[severity]}
                    transparent
                    opacity={0.3}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
        </group>
    );
};

// Arc connection between two points
interface ThreatArcProps {
    start: THREE.Vector3;
    end: THREE.Vector3;
    color: string;
}

const ThreatArc = ({ start, end, color }: ThreatArcProps) => {
    const curve = useMemo(() => {
        const midPoint = new THREE.Vector3()
            .addVectors(start, end)
            .multiplyScalar(0.5)
            .normalize()
            .multiplyScalar(1.3); // Arc height

        return new THREE.QuadraticBezierCurve3(start, midPoint, end);
    }, [start, end]);

    const points = curve.getPoints(50);
    const lineGeometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

    return (
        <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({
            color,
            transparent: true,
            opacity: 0.8,
            linewidth: 3,
        }))} />
    );
};

const Earth = () => {
    const groupRef = useRef<THREE.Group>(null);
    
    // Load high-quality Earth textures
    const [colorMap, normalMap, specularMap] = useLoader(THREE.TextureLoader, [
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg',
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_normal_2048.jpg',
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_specular_2048.jpg'
    ]);
    
    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.rotation.y += 0.002;
        }
    });

    return (
        <group ref={groupRef}>
            {/* Main Earth sphere with advanced materials */}
            <mesh>
                <sphereGeometry args={[1, 256, 256]} />
                <meshStandardMaterial
                    map={colorMap}
                    normalMap={normalMap}
                    normalScale={new THREE.Vector2(0.85, 0.85)}
                    roughnessMap={specularMap}
                    roughness={0.9}
                    metalness={0.1}
                />
            </mesh>
            {/* Subtle cloud layer */}
            <mesh scale={[1.003, 1.003, 1.003]}>
                <sphereGeometry args={[1, 128, 128]} />
                <meshStandardMaterial
                    color="#ffffff"
                    transparent
                    opacity={0.08}
                    roughness={1}
                    metalness={0}
                />
            </mesh>
            {/* Multi-layer atmosphere glow rings */}
            <mesh scale={[1.01, 1.01, 1.01]}>
                <sphereGeometry args={[1, 128, 128]} />
                <meshBasicMaterial
                    color="#10b981"
                    transparent
                    opacity={0.4}
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
            <mesh scale={[1.025, 1.025, 1.025]}>
                <sphereGeometry args={[1, 96, 96]} />
                <meshBasicMaterial
                    color="#10b981"
                    transparent
                    opacity={0.3}
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
            <mesh scale={[1.05, 1.05, 1.05]}>
                <sphereGeometry args={[1, 64, 64]} />
                <meshBasicMaterial
                    color="#059669"
                    transparent
                    opacity={0.2}
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
            <mesh scale={[1.1, 1.1, 1.1]}>
                <sphereGeometry args={[1, 48, 48]} />
                <meshBasicMaterial
                    color="#047857"
                    transparent
                    opacity={0.1}
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
        </group>
    );
};

interface GlobeSceneProps {
    markers: MarkerInput[];
    arcs: ArcInput[];
}

const GlobeScene = ({ markers, arcs }: GlobeSceneProps) => {
    const markerPositions = useMemo(() => {
        const map = new Map<string, THREE.Vector3>();
        markers.forEach((marker) => {
            map.set(marker.code, latLongToVector3(marker.lat, marker.lon, 1.02));
        });
        return map;
    }, [markers]);

    const threatMarkers = useMemo(() =>
        markers
            .map((marker) => {
                const position = markerPositions.get(marker.code);
                if (!position) return null;
                return {
                    id: marker.id,
                    position,
                    severity: marker.severity,
                };
            })
            .filter(Boolean) as Array<{ id: string; position: THREE.Vector3; severity: Severity }>,
        [markers, markerPositions]
    );

    const threatArcs = useMemo(() =>
        arcs
            .map((arc) => {
                const start = markerPositions.get(arc.originCode);
                const end = markerPositions.get(arc.targetCode);
                if (!start || !end) return null;
                return {
                    id: arc.id,
                    start,
                    end,
                    color: severityColors[arc.severity],
                };
            })
            .filter(Boolean) as Array<{ id: string; start: THREE.Vector3; end: THREE.Vector3; color: string }>,
        [arcs, markerPositions]
    );

    return (
        <>
            {/* Professional 3-point lighting setup */}
            <ambientLight intensity={0.4} color="#b0c4de" />
            
            {/* Key light - main illumination */}
            <directionalLight position={[5, 3, 5]} intensity={2} color="#ffffff" castShadow />
            
            {/* Fill light - soften shadows */}
            <directionalLight position={[-3, 1, -2]} intensity={0.8} color="#e0f2fe" />
            
            {/* Rim lights - edge definition */}
            <pointLight position={[0, 0, 5]} intensity={1.5} color="#ffffff" distance={10} />
            <pointLight position={[0, 0, -5]} intensity={0.6} color="#10b981" distance={10} />
            
            {/* Accent lights for atmosphere */}
            <pointLight position={[3, 3, 0]} intensity={0.8} color="#0ea5e9" distance={8} />
            <pointLight position={[-3, -3, 0]} intensity={0.6} color="#10b981" distance={8} />
            
            {/* Hemisphere light for natural look */}
            <hemisphereLight groundColor="#080820" color="#87ceeb" intensity={0.5} />
            <Stars radius={120} depth={100} count={15000} factor={7} saturation={0.1} fade speed={0.8} />
            
            <Earth />
            
            {/* Threat markers */}
            {threatMarkers.map((threat) => (
                <ThreatMarker
                    key={threat.id}
                    position={threat.position}
                    severity={threat.severity}
                />
            ))}

            {/* Connection arcs */}
            {threatArcs.map((arc) => (
                <ThreatArc
                    key={arc.id}
                    start={arc.start}
                    end={arc.end}
                    color={arc.color}
                />
            ))}

            <OrbitControls
                enableZoom={true}
                enablePan={false}
                minDistance={2}
                maxDistance={4}
                minPolarAngle={Math.PI / 4}
                maxPolarAngle={Math.PI / 1.3}
                autoRotate
                autoRotateSpeed={0.3}
            />
        </>
    );
};

const getSeverityFromMagnitude = (value: number): Severity => {
    if (value >= 15) return 'high';
    if (value >= 7) return 'medium';
    return 'low';
};

const normalizeRadarPairs = (pairs: RadarAttackPair[]) => {
    const markerMap = new Map<string, MarkerInput>();
    const arcList: ArcInput[] = [];
    let totalMagnitude = 0;

    const ensureMarker = (code: string, country: string, lat: number, lon: number, severity: Severity) => {
        const normalizedCode = code.toUpperCase();
        const existing = markerMap.get(normalizedCode);
        if (existing && severityRank[existing.severity] >= severityRank[severity]) {
            return existing;
        }

        const marker: MarkerInput = {
            id: normalizedCode,
            code: normalizedCode,
            country,
            lat,
            lon,
            severity,
        };
        markerMap.set(normalizedCode, marker);
        return marker;
    };

    pairs.forEach((pair, idx) => {
        const originCoords = getCountryCoordinates(pair.origin.code);
        const targetCoords = getCountryCoordinates(pair.target.code);
        if (!originCoords || !targetCoords) return;

        const severity = getSeverityFromMagnitude(pair.magnitude);
        ensureMarker(pair.origin.code, pair.origin.name, originCoords.lat, originCoords.lon, severity);
        ensureMarker(pair.target.code, pair.target.name, targetCoords.lat, targetCoords.lon, severity);

        arcList.push({
            id: pair.id ?? `${pair.origin.code}-${pair.target.code}-${idx}`,
            originCode: pair.origin.code.toUpperCase(),
            targetCode: pair.target.code.toUpperCase(),
            severity,
            magnitude: pair.magnitude,
        });
        totalMagnitude += pair.magnitude;
    });

    if (!arcList.length) {
        return null;
    }

    return {
        markers: Array.from(markerMap.values()),
        arcs: arcList,
        totalMagnitude,
    };
};

const Globe = () => {
    const [markers, setMarkers] = useState<MarkerInput[]>(fallbackMarkers);
    const [arcs, setArcs] = useState<ArcInput[]>(fallbackArcs);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [totalMagnitude, setTotalMagnitude] = useState<number>(fallbackArcs.reduce((sum, arc) => sum + arc.magnitude, 0));
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        const hydrate = async () => {
            setLoading(true);
            try {
                const pairs = await fetchRadarAttackPairs();
                const normalized = normalizeRadarPairs(pairs);
                if (!normalized) {
                    if (!cancelled) {
                        setError('Radar returned no attack pairs for the selected window.');
                    }
                    return;
                }

                if (!cancelled) {
                    setMarkers(normalized.markers);
                    setArcs(normalized.arcs);
                    setTotalMagnitude(normalized.totalMagnitude);
                    setLastUpdated(new Date());
                    setError(null);
                }
            } catch (err) {
                if (cancelled) return;
                const message = err instanceof Error ? err.message : 'Unable to reach Cloudflare Radar';
                setError(message);
                console.error('Radar globe feed error:', err);
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };

        hydrate();
        const interval = window.setInterval(hydrate, 60_000);
        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, []);

    const isLive = Boolean(lastUpdated);
    const formattedTime = lastUpdated
        ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : '—';
    const aggregatedShare = totalMagnitude ? totalMagnitude.toFixed(1) : '—';

    return (
        <div className="relative h-64 w-full overflow-hidden rounded-2xl bg-black shadow-inner">
            <Canvas
                camera={{ position: [0, 0, 3.2], fov: 45 }}
                gl={{ antialias: true, alpha: false }}
                style={{ background: '#000000' }}
            >
                <GlobeScene markers={markers} arcs={arcs} />
            </Canvas>

            <div className="absolute bottom-4 left-4 rounded-xl border border-white/10 bg-black/60 px-4 py-3 text-white backdrop-blur-md">
                <div className="flex items-center gap-2 text-xs font-semibold">
                    <div className="relative flex h-2 w-2">
                        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${isLive ? 'bg-emerald-300' : 'bg-amber-400'} opacity-70`}></span>
                        <span className={`relative inline-flex h-2 w-2 rounded-full ${isLive ? 'bg-emerald-400' : 'bg-amber-300'}`}></span>
                    </div>
                    <span>{isLive ? `${arcs.length} live attack corridors` : `${arcs.length} demo corridors`}</span>
                    {loading && (
                        <svg className="h-3.5 w-3.5 animate-spin text-white/70" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V2C6.477 2 2 6.477 2 12h2z" />
                        </svg>
                    )}
                </div>
                <div className="mt-1 text-[11px] text-white/70">
                    {isLive ? `Updated ${formattedTime}` : 'Awaiting Radar API token'}
                    {error && <span className="ml-2 text-rose-300">{error}</span>}
                </div>
                {isLive && (
                    <div className="mt-1 text-[11px] text-white/60">
                        Σ share: {aggregatedShare}% of mitigated requests (last 30m)
                    </div>
                )}
            </div>
        </div>
    );
};

export default Globe;
