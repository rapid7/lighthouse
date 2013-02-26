package com.logentries.lighthouse;

import java.util.Map;

public class Pull {
	private Info mInfo;
	private Map mData;

	public Pull(final Info info, final Map data) {
		mInfo = info;
		mData = data;
	}

        public Info getInfo() {
		return mInfo;
	}

	public Map getData() {
		return mData;
	}

	public String toString() {
		return String.format("{info:%s, data:%s}", mInfo, mData);
	}
}
