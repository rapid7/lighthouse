package com.logentries.lighthouse;

import java.util.LinkedHashMap;
import java.util.Map;

public class Copy {
	private static final String KEY_VERSION = "version";
	private static final String KEY_DATA = "data";

	private Version mVersion;
	private Map mData;

	public Copy(final Version version, final Map data) {
		mVersion = version;
		mData = data;
	}

	// FIXME: Handle parsing problems
	static public Copy fromMap(final Map map) {
		if (null == map) {
			return null;
		}
		Version version = Version.fromMap((Map)map.get(KEY_VERSION));
		Map data = (Map)map.get(KEY_DATA);
		return new Copy(version, data);
	}

	static public Map toMap(final Copy pull) {
		Map map = new LinkedHashMap();
		map.put(KEY_VERSION, Version.toMap(pull.getVersion()));
		map.put(KEY_DATA, pull.getData());
		return map;
	}

        public Version getVersion() {
		return mVersion;
	}

	public Map getData() {
		return mData;
	}

	public String toString() {
		return String.format("{%s:%s, %s:%s}", KEY_VERSION, getVersion(), KEY_DATA, getData());
	}
}
