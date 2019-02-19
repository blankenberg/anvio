FROM meren/anvio:5.3

ADD ./run_anvio_GIE.sh /

ENTRYPOINT ["/run_anvio_GIE.sh"]

EXPOSE 80
