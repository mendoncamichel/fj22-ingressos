package br.com.caelum.ingresso.rest;

import java.util.Optional;

import org.jboss.logging.Logger;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import br.com.caelum.ingresso.model.DetalhesDoFilme;
import br.com.caelum.ingresso.model.Filme;

public class ImbdClient {
	
	private Logger logger = Logger.getLogger(ImbdClient.class);
	
	public Optional<DetalhesDoFilme> request(Filme filme){
		
		RestTemplate client = new RestTemplate();
		
		String titulo = filme.getNome().replace(" ", "+");
		
		String url = String.format("https://imbd-fj22.herokuapp.com/imdb?title=%s", titulo);
		
		try {
			DetalhesDoFilme detalhesDoFilme = client.getForObject(url, DetalhesDoFilme.class);
			return Optional.of(detalhesDoFilme);
		}catch (RestClientException e){
			logger.error(e.getMessage(), e);
			return Optional.empty();
		}
	}
}
