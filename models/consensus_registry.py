"""Immutable governance metadata for market-consensus sources."""

from dataclasses import dataclass

from models.market_consensus import SourceCategory, _bounded, _required


ACCESS_METHODS = {"EXISTING_VALIDATED_SNAPSHOT", "OFFICIAL_PUBLIC_ENDPOINT", "MANUAL_IMPORT", "DETERMINISTIC_FIXTURE", "LICENSED_DATASET", "UNAVAILABLE"}
SOURCE_STATUSES = {"PUBLIC", "FIXTURE", "EXPORT", "UNAVAILABLE", "LICENSED"}
IMPLEMENTATION_STATUSES = {"ACTIVE_ADAPTER", "FIXTURE_ONLY", "IMPORT_ONLY", "UNAVAILABLE", "DEFERRED", "NOT_CONFIGURED"}


@dataclass(frozen=True)
class ConsensusSourceRecord:
    source_id: str
    display_name: str
    category: SourceCategory
    official_homepage: str
    approved_access_method: str
    authentication_requirement: str
    licensing_status: str
    rate_limit: str
    supported_symbols: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    expected_update_seconds: int
    freshness_threshold_seconds: int
    default_reliability: float
    enabled_by_default: bool
    source_status: str
    implementation_status: str
    known_limitations: tuple[str, ...]
    terms_note: str
    attribution_requirements: str
    historical_evaluation_allowed: bool

    def __post_init__(self) -> None:
        for value, name in ((self.source_id, "source_id"), (self.display_name, "display_name"), (self.official_homepage, "official_homepage"), (self.authentication_requirement, "authentication_requirement"), (self.licensing_status, "licensing_status"), (self.rate_limit, "rate_limit"), (self.terms_note, "terms_note"), (self.attribution_requirements, "attribution_requirements")):
            _required(value, name)
        if not isinstance(self.category, SourceCategory):
            raise ValueError("category must be a SourceCategory.")
        if self.approved_access_method not in ACCESS_METHODS:
            raise ValueError("approved_access_method is not governed.")
        if self.source_status not in SOURCE_STATUSES:
            raise ValueError("source_status is not governed.")
        if self.implementation_status not in IMPLEMENTATION_STATUSES:
            raise ValueError("implementation_status is not governed.")
        if not self.supported_symbols or not self.supported_timeframes:
            raise ValueError("Sources require explicit symbol and timeframe support.")
        if self.expected_update_seconds <= 0 or self.freshness_threshold_seconds <= 0:
            raise ValueError("Source timing controls must be positive.")
        _bounded(self.default_reliability, "default_reliability")
        if self.enabled_by_default:
            raise ValueError("Consensus sources cannot silently enable by default.")
        lowered = " ".join((self.authentication_requirement, self.terms_note, self.attribution_requirements)).lower()
        if any(term in lowered for term in ("secret", "password", "private exchange", "trading credential")):
            raise ValueError("Source records cannot store or request secrets or trading credentials.")


def governed_sources() -> tuple[ConsensusSourceRecord, ...]:
    """Return the deterministic built-in catalog; no source is activated here."""
    all_symbols = ("BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD")
    all_timeframes = ("5M", "15M", "1H", "4H", "1D")
    return (
        ConsensusSourceRecord("hermes-public-market", "Hermes Validated Public Market Evidence", SourceCategory.PUBLIC_EXCHANGE_METRICS, "https://www.hermesquantlabs.local", "EXISTING_VALIDATED_SNAPSHOT", "NONE", "INTERNAL_DERIVATION_FROM_PUBLIC_DATA", "INHERITS_EXISTING_PROVIDER_LIMITS", all_symbols, all_timeframes, 30, 180, 0.82, False, "PUBLIC", "ACTIVE_ADAPTER", ("Derived from existing exchange observations and not independent of those providers.",), "Reuse only validated snapshots already collected by Hermes.", "Retain provider names and observation timestamps.", True),
        ConsensusSourceRecord("fear-greed-public", "Broad Market Fear and Greed", SourceCategory.SENTIMENT, "https://alternative.me/crypto/fear-and-greed-index/", "OFFICIAL_PUBLIC_ENDPOINT", "NONE", "PUBLIC_ENDPOINT_TERMS_REQUIRE_REVIEW", "DOCUMENTED_PUBLIC_LIMITS", ("MARKET-WIDE",), ("1D",), 86400, 172800, 0.45, False, "UNAVAILABLE", "DEFERRED", ("Broad-market sentiment is not symbol-specific.", "Access and endpoint behavior must be verified before activation."), "Use only the documented public endpoint and retain attribution.", "Attribute Alternative.me and retain the public reference.", True),
        ConsensusSourceRecord("coingecko-public-metadata", "CoinGecko Public Market Metadata", SourceCategory.MARKET_BREADTH, "https://www.coingecko.com/", "OFFICIAL_PUBLIC_ENDPOINT", "NONE", "PUBLIC_ENDPOINT_TERMS_REQUIRE_REVIEW", "DOCUMENTED_PUBLIC_LIMITS", all_symbols, ("1H", "4H", "1D"), 300, 900, 0.6, False, "UNAVAILABLE", "DEFERRED", ("Public access may be rate-limited or require a configured licensed plan.",), "Activate only after official endpoint and usage terms are verified.", "Attribute CoinGecko when its data is displayed.", True),
        ConsensusSourceRecord("derivatives-fixture", "Derivatives Crowding Fixture", SourceCategory.DERIVATIVES, "https://docs.hermesquantlabs.local/consensus", "DETERMINISTIC_FIXTURE", "NONE", "TEST_FIXTURE_ONLY", "NOT_APPLICABLE", all_symbols, all_timeframes, 60, 300, 0.5, False, "FIXTURE", "FIXTURE_ONLY", ("Synthetic funding, open-interest, liquidation, and long/short observations are not live market facts.",), "Tests and demonstrations only.", "Label every observation FIXTURE.", True),
        ConsensusSourceRecord("onchain-manual-import", "On-chain Manual Import", SourceCategory.ON_CHAIN, "https://docs.hermesquantlabs.local/consensus", "MANUAL_IMPORT", "USER_PROVIDED_EXPORT", "USER_RESPONSIBLE_FOR_DATA_RIGHTS", "NOT_APPLICABLE", all_symbols, ("1H", "4H", "1D"), 3600, 7200, 0.5, False, "EXPORT", "IMPORT_ONLY", ("Hermes cannot verify upstream methodology or licensing from the record alone.",), "Operator must confirm permitted use before import.", "Retain provider, author, timestamp, and reference.", True),
        ConsensusSourceRecord("analyst-community-import", "Analyst and Community Manual Import", SourceCategory.ANALYST_COMMUNITY, "https://docs.hermesquantlabs.local/consensus", "MANUAL_IMPORT", "USER_PROVIDED_EXPORT", "USER_RESPONSIBLE_FOR_DATA_RIGHTS", "NOT_APPLICABLE", all_symbols, all_timeframes, 900, 3600, 0.35, False, "EXPORT", "IMPORT_ONLY", ("Popularity does not establish expertise or predictive accuracy.", "Do not store full posts or articles."), "No scraping; accept only permitted operator-provided normalized records.", "Retain author/source attribution and a short compliant summary.", True),
        ConsensusSourceRecord("licensed-onchain-unconfigured", "Licensed On-chain Dataset", SourceCategory.ON_CHAIN, "https://docs.hermesquantlabs.local/consensus", "LICENSED_DATASET", "LICENSED_CONFIGURATION_REQUIRED", "LICENSE_REQUIRED", "PROVIDER_SPECIFIC", all_symbols, ("1H", "4H", "1D"), 3600, 7200, 0.65, False, "LICENSED", "NOT_CONFIGURED", ("No licensed provider is configured.",), "Remain inactive until licensing and approved integration are reviewed.", "Follow the selected provider's attribution terms.", True),
    )
