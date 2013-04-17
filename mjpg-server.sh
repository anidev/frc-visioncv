#! /bin/bash

sleep 2
echo "HTTP/1.1 200 OK"
echo "Connection: close"
echo "Server: mjpg-server"
echo "Cache-Control: no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0"
echo "Pragma: no-cache"
echo -e "Content-Type: multipart/x-mixed-replace; boundary=ASDFBOUNDARY\n"
while [ true ]
do
	for FILE in `find -maxdepth 1 -type f -name "*.jpg"`
	do
		MIME=`file --mime "$FILE" | awk '{print $2}' | sed 's/;//'`
		LENGTH=`du -b "$FILE" | awk '{print $1}'`
		TIME=`date +%s`
#		if [ "x`echo $MIME | sed -r 's/\;.*//'`" = "xtext/plain" ]
#		then
			echo -e "--ASDFBOUNDARY"
			echo "Content-Type: $MIME"
			echo "Content-Length: $LENGTH"
			echo -e "X-Timestamp: $TIME\n"
			cat $FILE
			echo
#		fi
	done
done
echo -e "Content-Type: text/html; charset=ascii\n"
echo "All done"
echo "--ASDFBOUNDARY"
