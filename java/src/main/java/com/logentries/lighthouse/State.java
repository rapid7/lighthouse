package com.logentries.lighthouse;

import java.util.Map;
import java.util.LinkedHashMap;

public class State {
	private static final String KEY_VERSION = "version";

	private Version mVersion;

	// FIXME: Add info about servers
	public State(final Version version) {
		mVersion = version;
	}

	// FIXME: Add parser exceptions
	@SuppressWarnings("unchecked")
	public static State fromMap(final Map<String, Object> map) {
		return new State(Version.fromMap((Map<String, Object>)map.get(KEY_VERSION)));
	}

	public static Map<String, Object> toMap(final State state) {
		final Map<String, Object> map = new LinkedHashMap<String, Object>();
		map.put(KEY_VERSION, state.getVersion());
		return map;
	}

	public Version getVersion() {
		return mVersion;
	}
}
