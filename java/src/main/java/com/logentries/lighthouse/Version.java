package com.logentries.lighthouse;

import java.util.Map;
import java.util.LinkedHashMap;

public class Version {
	private static final String KEY_SEQUENCE = "sequence";
	private static final String KEY_CHECKSUM = "checksum";

	private int mSequence;
	private String mChecksum;

	public Version(final int sequence, final String checksum) {
		if (sequence < 0) {
			throw new IllegalArgumentException("version should be >= 0");
		}
		mSequence = sequence;
		mChecksum = checksum;
	}

	// FIXME: handle parsing exceptions
	public static Version fromMap(final Map<String, Object> map) {
		if (null == map) {
			return null;
		}
		return new Version(((Number)map.get(KEY_SEQUENCE)).intValue(), (String)map.get(KEY_CHECKSUM));
	}

	public static Map<String, Object> toMap(final Version version) {
		Map<String, Object> map = new LinkedHashMap<String, Object>();
		map.put(KEY_SEQUENCE, version.getSequence());
		map.put(KEY_CHECKSUM, version.getChecksum());
		return map;
	}

	public int getSequence() {
		return mSequence;
	}

	public String getChecksum() {
		return mChecksum;
	}

	public boolean equals(final Object o) {
		if (!(o instanceof Version)) {
			return false;
		}
		final Version version = (Version)o;
		return getSequence() == version.getSequence() && getChecksum().equals(version.getChecksum());
	}
	
	public String toString() {
		return String.format("{sequence:%d; checksum:%s}", getSequence(), getChecksum());
	}
}
