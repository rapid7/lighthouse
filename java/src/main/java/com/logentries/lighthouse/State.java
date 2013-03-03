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
	public static State fromMap(final Map map) {
		return new State(Version.fromMap((Map)map.get(KEY_VERSION)));
	}

	public static Map toMap(final State state) {
		final Map map = new LinkedHashMap();
		map.put(KEY_VERSION, state.getVersion());
		return map;
	}

	public Version getVersion() {
		return mVersion;
	}
}
