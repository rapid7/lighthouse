package com.logentries.lighthouse;

import java.util.LinkedHashMap;
import java.util.Map;

public class Copy {
	private static final String KEY_VERSION = "version";
	private static final String KEY_DATA = "data";

	private Version mVersion;
	private Map<String, Object> mData;

	public Copy(final Version version, final Map<String, Object> data) {
		mVersion = version;
		mData = data;
	}

	// FIXME: Handle parsing problems
	static public Copy fromMap(final Map<String, Object> map) {
		if (null == map) {
			return null;
		}
		@SuppressWarnings("unchecked")
		Version version = Version.fromMap((Map<String, Object>)map.get(KEY_VERSION));
		@SuppressWarnings("unchecked")
		Map<String, Object> data = (Map<String, Object>)map.get(KEY_DATA);
		return new Copy(version, data);
	}

	static public Map<String, Object> toMap(final Copy pull) {
		Map<String, Object> map = new LinkedHashMap<String, Object>();
		map.put(KEY_VERSION, Version.toMap(pull.getVersion()));
		map.put(KEY_DATA, pull.getData());
		return map;
	}

        public Version getVersion() {
		return mVersion;
	}

	public Map<String, Object> getData() {
		return mData;
	}

	public String toString() {
		return String.format("{%s:%s, %s:%s}", KEY_VERSION, getVersion(), KEY_DATA, getData());
	}
}
