"""Tests for reference profile loading and validation.

Covers REF-01 through REF-08: profile data, loading, listing, search order,
malformed rejection, and alias resolution.
"""

import json

import pytest

from phantom import (
    ProfileLoadError,
    ReferenceProfile,
    list_profiles,
    load_profile,
)
from phantom.exceptions import PhantomError


# Expected genre names per REF-01 / D-03
ALL_GENRES = [
    "ambient",
    "edm",
    "electronic",
    "hip-hop",
    "lo-fi",
    "metal",
    "pop",
    "rock",
    "rock-metal",
]

# Frequency band keys matching spectral.py _BAND_LABELS
EXPECTED_BANDS = [
    "31_hz",
    "62_hz",
    "125_hz",
    "250_hz",
    "500_hz",
    "1000_hz",
    "2000_hz",
    "4000_hz",
    "8000_hz",
    "16000_hz",
]


class TestProfileLoadError:
    """ProfileLoadError exception behavior."""

    def test_inherits_from_phantom_error(self):
        assert issubclass(ProfileLoadError, PhantomError)

    def test_inherits_from_exception(self):
        assert issubclass(ProfileLoadError, Exception)


class TestAllGenresLoadable:
    """REF-01: All 9 genre profiles exist and load successfully."""

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_genre_loads(self, genre):
        profile = load_profile(genre)
        assert isinstance(profile, ReferenceProfile)
        assert profile.genre == genre

    def test_total_builtin_count(self):
        profiles = list_profiles()
        assert len(profiles) == 9


class TestLoudnessTargets:
    """REF-02: Each profile contains loudness targets."""

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_lufs_range_is_two_floats(self, genre):
        profile = load_profile(genre)
        assert len(profile.loudness.lufs_range) == 2
        assert profile.loudness.lufs_range[0] < profile.loudness.lufs_range[1]

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_crest_factor_range_is_two_floats(self, genre):
        profile = load_profile(genre)
        assert len(profile.loudness.crest_factor_range) == 2
        assert (
            profile.loudness.crest_factor_range[0]
            < profile.loudness.crest_factor_range[1]
        )

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_true_peak_max_is_negative(self, genre):
        profile = load_profile(genre)
        assert profile.loudness.true_peak_max_dbtp < 0


class TestFrequencyTargets:
    """REF-03: Each profile contains frequency targets per octave band."""

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_all_10_bands(self, genre):
        profile = load_profile(genre)
        assert sorted(profile.frequency.bands.keys()) == sorted(EXPECTED_BANDS)

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_band_values_are_floats(self, genre):
        profile = load_profile(genre)
        for band, value in profile.frequency.bands.items():
            assert isinstance(value, (int, float)), f"{genre}/{band} is not numeric"


class TestStereoConventions:
    """REF-04: Each profile contains stereo conventions."""

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_width(self, genre):
        profile = load_profile(genre)
        assert profile.stereo.width in ("narrow", "moderate", "wide", "very_wide")

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_mono_below_hz(self, genre):
        profile = load_profile(genre)
        assert profile.stereo.mono_below_hz > 0


class TestSpatialConventions:
    """REF-05: Each profile contains spatial conventions and processing notes."""

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_reverb_type(self, genre):
        profile = load_profile(genre)
        assert profile.spatial.reverb_type in (
            "plate",
            "room",
            "hall",
            "spring",
            "minimal",
        )

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_reverb_amount(self, genre):
        profile = load_profile(genre)
        assert profile.spatial.reverb_amount in ("dry", "subtle", "moderate", "lush")

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_pre_delay(self, genre):
        profile = load_profile(genre)
        assert profile.spatial.pre_delay_ms in ("short", "medium", "long")

    @pytest.mark.parametrize("genre", ALL_GENRES)
    def test_has_processing_notes(self, genre):
        profile = load_profile(genre)
        assert len(profile.processing_notes) > 20  # meaningful text, not empty


class TestSearchOrder:
    """REF-06: Loader searches env var first, then builtins."""

    def test_user_dir_overrides_builtin(self, tmp_path, monkeypatch):
        """User profile in PHANTOM_PROFILES_DIR replaces builtin entirely (D-10)."""
        custom_profile = {
            "genre": "rock",
            "description": "Custom rock profile from user directory",
            "loudness": {
                "lufs_range": [-14.0, -10.0],
                "crest_factor_range": [8.0, 14.0],
                "true_peak_max_dbtp": -0.5,
            },
            "frequency": {
                "bands": {k: 0.0 for k in EXPECTED_BANDS},
            },
            "stereo": {"width": "narrow", "mono_below_hz": 200.0},
            "spatial": {
                "reverb_type": "hall",
                "reverb_amount": "lush",
                "pre_delay_ms": "long",
            },
            "processing_notes": "Custom test profile overriding built-in rock.",
        }
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(custom_profile))

        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        result = load_profile("rock")
        assert result.description == "Custom rock profile from user directory"
        assert result.loudness.lufs_range == (-14.0, -10.0)

    def test_falls_back_to_builtin_when_no_env(self, monkeypatch):
        """Without PHANTOM_PROFILES_DIR, loads builtin profiles."""
        monkeypatch.delenv("PHANTOM_PROFILES_DIR", raising=False)
        result = load_profile("rock")
        assert result.genre == "rock"
        assert "Custom" not in result.description


class TestMalformedProfile:
    """REF-07: Malformed profiles are rejected with clear error."""

    def test_missing_required_field(self, tmp_path, monkeypatch):
        """Profile missing 'loudness' raises ProfileLoadError."""
        bad_profile = {"genre": "test", "description": "missing fields"}
        (tmp_path / "test.json").write_text(json.dumps(bad_profile))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))

        with pytest.raises(ProfileLoadError, match="malformed"):
            load_profile("test")

    def test_invalid_json_syntax(self, tmp_path, monkeypatch):
        """File with invalid JSON raises error."""
        (tmp_path / "broken.json").write_text("{not valid json")
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))

        with pytest.raises(ProfileLoadError, match="invalid JSON"):
            load_profile("broken")

    def test_wrong_field_type(self, tmp_path, monkeypatch):
        """Profile with wrong field types raises ProfileLoadError."""
        bad_profile = {
            "genre": "test",
            "description": "wrong types",
            "loudness": {
                "lufs_range": "not a tuple",
                "crest_factor_range": [1, 2],
                "true_peak_max_dbtp": -1.0,
            },
            "frequency": {"bands": {}},
            "stereo": {"width": "wide", "mono_below_hz": 100.0},
            "spatial": {
                "reverb_type": "room",
                "reverb_amount": "moderate",
                "pre_delay_ms": "short",
            },
            "processing_notes": "test",
        }
        (tmp_path / "test.json").write_text(json.dumps(bad_profile))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))

        with pytest.raises(ProfileLoadError, match="malformed"):
            load_profile("test")


class TestListProfiles:
    """REF-08: User can list all available profiles."""

    def test_returns_sorted_list(self):
        profiles = list_profiles()
        assert profiles == sorted(profiles)

    def test_contains_all_genres(self):
        profiles = list_profiles()
        for genre in ALL_GENRES:
            assert genre in profiles

    def test_includes_user_profiles(self, tmp_path, monkeypatch):
        """User profiles appear in list alongside builtins."""
        custom = {
            "genre": "custom-genre",
            "description": "test",
            "loudness": {
                "lufs_range": [-10.0, -7.0],
                "crest_factor_range": [5.0, 9.0],
                "true_peak_max_dbtp": -1.0,
            },
            "frequency": {"bands": {k: 0.0 for k in EXPECTED_BANDS}},
            "stereo": {"width": "moderate", "mono_below_hz": 100.0},
            "spatial": {
                "reverb_type": "room",
                "reverb_amount": "moderate",
                "pre_delay_ms": "short",
            },
            "processing_notes": "custom test profile for listing",
        }
        (tmp_path / "custom-genre.json").write_text(json.dumps(custom))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))

        profiles = list_profiles()
        assert "custom-genre" in profiles
        assert len(profiles) == 10  # 9 builtin + 1 custom


class TestCaseInsensitive:
    """D-07: Case-insensitive profile lookup."""

    @pytest.mark.parametrize("variant", ["Rock", "ROCK", "rOcK", " rock "])
    def test_case_variants_resolve(self, variant):
        profile = load_profile(variant)
        assert profile.genre == "rock"


class TestAliases:
    """D-08: Common alias resolution."""

    @pytest.mark.parametrize(
        "alias, expected",
        [
            ("hiphop", "hip-hop"),
            ("hip hop", "hip-hop"),
            ("lofi", "lo-fi"),
            ("lo fi", "lo-fi"),
            ("rockmetal", "rock-metal"),
            ("rock metal", "rock-metal"),
        ],
    )
    def test_alias_resolves(self, alias, expected):
        profile = load_profile(alias)
        assert profile.genre == expected


class TestMissingProfile:
    """Missing profile error includes available profiles."""

    def test_missing_profile_lists_available(self):
        with pytest.raises(ProfileLoadError, match="Available profiles") as exc_info:
            load_profile("nonexistent")
        assert "No profile found" in str(exc_info.value)


class TestUserProfileSizeGuard:
    """X-WR-02: User profile files are checked for size (1MB max)."""

    def test_user_profile_size_guard(self, tmp_path, monkeypatch):
        """Profile file > 1MB raises ProfileLoadError with 'too large'."""
        # Create a 2MB JSON file
        big_content = '{"genre": "big", "data": "' + "x" * (2 * 1_000_000) + '"}'
        (tmp_path / "big.json").write_text(big_content)
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))

        with pytest.raises(ProfileLoadError, match="too large"):
            load_profile("big")


class TestUserProfileSymlinkEscape:
    """X-WR-03 / S-WR-04: Path resolution uses realpath containment."""

    def test_user_profile_symlink_escape(self, tmp_path, monkeypatch):
        """Symlink inside profiles dir pointing outside raises ProfileLoadError."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        # Create a target file outside the profiles dir
        outside_file = tmp_path / "secret.json"
        outside_file.write_text('{"genre": "secret"}')
        # Create a symlink inside the profiles dir pointing outside
        try:
            symlink = profiles_dir / "escape.json"
            symlink.symlink_to(outside_file)
        except OSError:
            pytest.skip("Platform does not support symlinks")
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(profiles_dir))

        with pytest.raises(ProfileLoadError, match="Invalid profile name"):
            load_profile("escape")


class TestFrozenProfile:
    """ReferenceProfile is immutable (frozen=True)."""

    def test_cannot_modify_genre(self):
        profile = load_profile("rock")
        with pytest.raises(Exception):  # ValidationError for frozen model
            profile.genre = "changed"


def _make_user_rock_profile():
    return {
        "genre": "rock",
        "description": "Custom user rock",
        "loudness": {
            "lufs_range": [-14.0, -10.0],
            "crest_factor_range": [8.0, 14.0],
            "true_peak_max_dbtp": -0.5,
        },
        "frequency": {"bands": {k: 0.0 for k in EXPECTED_BANDS}},
        "stereo": {"width": "narrow", "mono_below_hz": 200.0},
        "spatial": {
            "reverb_type": "hall",
            "reverb_amount": "lush",
            "pre_delay_ms": "long",
        },
        "processing_notes": "Custom user rock profile.",
    }


class TestShadowWarning:
    """User profile shadowing a built-in emits a warning."""

    def test_shadow_warning_emitted(self, tmp_path, monkeypatch, caplog):
        """Overriding a built-in profile logs an info-level warning."""
        import logging

        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(_make_user_rock_profile()))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.delenv("PHANTOM_PROFILE_OVERRIDE_QUIET", raising=False)

        with caplog.at_level(logging.INFO, logger="phantom._profiles"):
            load_profile("rock")
        assert "overrides built-in" in caplog.text

    def test_shadow_warning_suppressed(self, tmp_path, monkeypatch, caplog):
        """PHANTOM_PROFILE_OVERRIDE_QUIET=1 suppresses the warning."""
        import logging

        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(_make_user_rock_profile()))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.setenv("PHANTOM_PROFILE_OVERRIDE_QUIET", "1")

        with caplog.at_level(logging.INFO, logger="phantom._profiles"):
            load_profile("rock")
        assert "overrides built-in" not in caplog.text

    def test_no_warning_for_custom_only(self, tmp_path, monkeypatch, caplog):
        """No warning when user profile doesn't shadow a built-in."""
        import logging

        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        custom = _make_user_rock_profile()
        custom["genre"] = "my-custom"
        profile_path = tmp_path / "my-custom.json"
        profile_path.write_text(json.dumps(custom))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.delenv("PHANTOM_PROFILE_OVERRIDE_QUIET", raising=False)

        with caplog.at_level(logging.INFO, logger="phantom._profiles"):
            load_profile("my-custom")
        assert "overrides built-in" not in caplog.text


class TestProfileMerge:
    """PHANTOM_PROFILE_MERGE=1 merges user fields over built-in."""

    def test_merge_mode(self, tmp_path, monkeypatch):
        """User fields override built-in, missing fields fall through."""
        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        partial = {"description": "Merged rock description"}
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(partial))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.setenv("PHANTOM_PROFILE_MERGE", "1")
        monkeypatch.setenv("PHANTOM_PROFILE_OVERRIDE_QUIET", "1")

        result = load_profile("rock")
        assert result.description == "Merged rock description"
        assert result.genre == "rock"
        assert result.loudness is not None

    def test_deep_merge_preserves_nested_keys(self, tmp_path, monkeypatch):
        """Overriding one nested key preserves sibling keys."""
        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        partial = {"loudness": {"lufs_range": [-20.0, -14.0]}}
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(partial))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.setenv("PHANTOM_PROFILE_MERGE", "1")
        monkeypatch.setenv("PHANTOM_PROFILE_OVERRIDE_QUIET", "1")

        result = load_profile("rock")
        assert result.loudness.lufs_range == (-20.0, -14.0)
        assert result.loudness.crest_factor_range is not None
        assert result.loudness.true_peak_max_dbtp is not None


class TestProfileMtimeCache:
    """Profile changes are picked up via mtime without server restart."""

    def test_mtime_cache_invalidation(self, tmp_path, monkeypatch):
        """Editing a user profile mid-session reloads on next call."""
        import time
        from phantom._profiles import _profile_cache

        _profile_cache.clear()
        profile_data = _make_user_rock_profile()
        profile_path = tmp_path / "rock.json"
        profile_path.write_text(json.dumps(profile_data))
        monkeypatch.setenv("PHANTOM_PROFILES_DIR", str(tmp_path))
        monkeypatch.setenv("PHANTOM_PROFILE_OVERRIDE_QUIET", "1")

        result1 = load_profile("rock")
        assert result1.description == "Custom user rock"

        time.sleep(0.05)
        profile_data["description"] = "Updated mid-session"
        profile_path.write_text(json.dumps(profile_data))

        result2 = load_profile("rock")
        assert result2.description == "Updated mid-session"
